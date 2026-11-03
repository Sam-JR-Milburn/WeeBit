set dotenv-load := true

db-up:
    docker compose up -d --wait

# Install
install:
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt install -y nodejs
    cd frontend && npm install
    cd backend && uv sync
    cp example.env .env

# Make schema changes
db-migrate env_file=".env":
    PYTHONPATH=backend/src ENV_FILE=../.env uv --directory backend run uvicorn weebit.main:app --reload --port 8080

# Start the backend API
backend-prod: db-up (db-migrate ".env")
    PYTHONPATH=backend/src ENV_FILE=../.env uv --directory backend run uvicorn weebit.main:app --reload --port 8080
    
frontend-dev:
    cd frontend && npm run dev

ensure-frontend-is-built:
    @test -d frontend/.next || (echo "Frontend build not found. Building Next.js..." && cd frontend && npm run build)

# Run the NextJS frontend.
frontend-prod: ensure-frontend-is-built
    cd frontend && npm run start

# Run the app system, await service startup and DB migrations
[parallel]
prod: backend-prod frontend-prod

[parallel]
dev: backend-prod frontend-dev
    
# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v
    rm -rf frontend/.next

# Deploy to Terraform (IaC)

backend-build:
    rm -f backend.zip
    find backend -type d -name "__pycache__" -exec rm -rf {} +
    find backend -name "*.pyc" -delete
    cd backend && uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt
    cd backend && zip -r ../backend.zip . -x ".venv/*" "antenv/*" "*.pyc" "__pycache__/*" ".git/*"

backend-deploy: backend-build
    az webapp deployment source config-zip \
        --resource-group rg-weebit-production \
        --name app-weebit-api \
        --src backend.zip
    
frontend-build:
    @if [ ! -f "frontend/.env.production" ]; then \
        echo "Error: frontend/.env.production file not found! Please create it before building."; \
        exit 1; \
    fi
    cd frontend && npm install && npm run build
    rm -f frontend.zip
    cd frontend && zip -r ../frontend.zip . -x ".next/cache/*"

frontend-deploy: frontend-build
    az webapp deploy \
    --resource-group rg-weebit-production \
    --name app-weebit-frontend \
    --src-path frontend.zip \
    --type zip 

build-all: backend-build frontend-build

# Optional: if you need the RedisPassword or PostgresPassword to be specific.
set-secret name:
    #!/usr/bin/env bash
    read -sp "Enter value for {{name}}: " secret_value
    echo ""
    az keyvault secret set \
      --vault-name kv-weebit-prod \
      --name "{{name}}" \
      --value "$secret_value"
    echo "Successfully set secret '{{name}}' in kv-weebit-prod."

clean-rg:
    #!/usr/bin/env bash
    if [ "$(az group exists --name rg-weebit-production)" = "true" ]; then
        echo "Resource group exists. Deleting..."
        az group delete --name rg-weebit-production --yes --no-wait
    else
        echo "Resource group 'rg-weebit-production' does not exist. Skipping."
    fi

clean-tf-state:
    rm -rf .terraform .terraform.lock.hcl tfplan

tf-imports:
    #!/usr/bin/env bash
    if az keyvault show --name "kv-weebit-prod" --resource-group "rg-weebit-production" &>/dev/null; then
        echo "Key Vault 'kv-weebit-prod' exists. Importing existing resources into state..."
        
        # Using || true ensures that if an individual secret version has changed or is already imported, it won't crash the entire import block.
        terraform import azurerm_key_vault_access_policy.terraform_user \
        "/subscriptions/adf59a08-f032-4e29-aeb0-654a4183ca7a/resourceGroups/rg-weebit-production/providers/Microsoft.KeyVault/vaults/kv-weebit-prod/objectId/c00a422b-673f-46a1-8596-fb8de9517376" || true
        
        terraform import azurerm_key_vault_secret.frontend_url_sec \
        "https://kv-weebit-prod.vault.azure.net/secrets/NextPublicFrontendUrl/f896f4d7eb64413abbcb4b27f238dd57" || true
        
        terraform import azurerm_key_vault_secret.postgres_user \
        "https://kv-weebit-prod.vault.azure.net/secrets/PostgresUser/cb5dc6061fde400785b0c3f44d63f159" || true
        
        terraform import azurerm_key_vault_secret.postgres_password \
        "https://kv-weebit-prod.vault.azure.net/secrets/PostgresPassword/5019ddb0573645529defd23fca563f9c" || true
        
        terraform import azurerm_key_vault_secret.postgres_db \
        "https://kv-weebit-prod.vault.azure.net/secrets/PostgresDbName/5261ca7aec0440a6aea462972d5e3fb4" || true
        
        terraform import azurerm_key_vault_secret.postgres_port \
        "https://kv-weebit-prod.vault.azure.net/secrets/PostgresPort/9f2dba50476f41688fc73e0fe02fd505" || true
        
        terraform import azurerm_key_vault_secret.postgres_host \
        "https://kv-weebit-prod.vault.azure.net/secrets/PostgresHost/dd7ac1ad94e8408da63285f54fe50308" || true
        
        terraform import azurerm_key_vault_secret.backend_host \
        "https://kv-weebit-prod.vault.azure.net/secrets/BackendHost/48acc972054f46258f9e2a987862ee2a" || true
        
        terraform import azurerm_key_vault_secret.backend_port \
        "https://kv-weebit-prod.vault.azure.net/secrets/BackendPort/b1bde9df6c2a45298d2e9e27040de40b" || true
        
        terraform import azurerm_key_vault_secret.allowed_origins \
        "https://kv-weebit-prod.vault.azure.net/secrets/AllowedOrigins/f30a3cd825b64100b42889801e08bfad" || true
        
        terraform import azurerm_key_vault_secret.redis_url \
        "https://kv-weebit-prod.vault.azure.net/secrets/RedisUrl/510fc90551a54c8a87522fff95784203" || true
        
        terraform import azurerm_key_vault_secret.redis_port \
        "https://kv-weebit-prod.vault.azure.net/secrets/RedisPort/997602991a794bed83b4ab75dc8da158" || true
        
        terraform import azurerm_key_vault_secret.redis_password \
        "https://kv-weebit-prod.vault.azure.net/secrets/RedisPassword/b17dc0943916494aa30bc1f5b6a515b0" || true
        
        terraform import azurerm_key_vault_secret.backend_url_sec \
        "https://kv-weebit-prod.vault.azure.net/secrets/NextPublicApiUrl/cb548e13938f47eb9be1a51688b63655" || true
    else
        echo "Key Vault 'kv-weebit-prod' does not exist yet. Skipping imports."
    fi

deploy: tf-imports
    terraform init
    terraform plan -out=tfplan
    terraform apply -parallelism=2 -auto-approve tfplan

deploy-applications:
    @echo "Triggering deployments..."
    just backend-deploy & just frontend-deploy & wait

full-deploy: clean-tf-state tf-imports
    terraform init
    terraform plan -out=tfplan
    terraform apply -parallelism=2 -auto-approve tfplan
    @echo "Triggering deployments..."
    just backend-deploy & just frontend-deploy & wait
