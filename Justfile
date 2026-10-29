set dotenv-load := true

db-up:
    docker compose up -d --wait

# Install
install:
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt install -y nodejs
    cd frontend && npm install
    cd backend && uv sync

# Make schema changes
db-migrate env_file=".env":
    PYTHONPATH=backend/src ENV_FILE=.env uv --directory backend run uvicorn weebit.main:app --reload --port 8080

# Start the backend API
backend-prod: db-up (db-migrate ".env")
    PYTHONPATH=backend/src ENV_FILE=.env uv run uvicorn weebit.main:app --reload --port 8080

ensure-frontend-is-built:
    @test -d frontend/.next || (echo "Frontend build not found. Building Next.js..." && cd frontend && npm run build)

# Run the NextJS frontend.
frontend-prod: ensure-frontend-is-built
    cd frontend && npm run start

# Run the app system, await service startup and DB migrations
[parallel]
prod: backend-prod frontend-prod
    
# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v
    rm -rf frontend/.next

# Deploy to Terraform (IaC)

backend-build:
    cd backend && \
    uv export --no-hashes --format requirements-txt -o requirements.txt && \
    grep -v '^-e' requirements.txt > clean-requirements.txt && \
    mv clean-requirements.txt requirements.txt
    rm -f backend.zip
    cd backend && zip -r ../backend.zip . -x ".venv/*" "antenv/*" "*.pyc" "__pycache__/*"

backend-deploy: backend-build
    az webapp start --resource-group rg-weebit-production --name app-weebit-api
    az webapp deploy \
    --resource-group rg-weebit-production \
    --name app-weebit-api \
    --src-path backend.zip
    --type zip
    
frontend-build:
    rm -f frontend.zip
    cd frontend && zip -r ../frontend.zip . -x "node_modules/*" ".next/*"

frontend-deploy: frontend-build
    az webapp start --resource-group rg-weebit-production --name app-weebit-frontend
    az webapp deploy \
    --resource-group rg-weebit-production \
    --name app-weebit-frontend \
    --src-path frontend.zip
    --type zip

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
    - terraform import azurerm_key_vault_access_policy.terraform_user \
    "/subscriptions/adf59a08-f032-4e29-aeb0-654a4183ca7a/resourceGroups/rg-weebit-production/providers/Microsoft.KeyVault/vaults/kv-weebit-prod/objectId/c00a422b-673f-46a1-8596-fb8de9517376"
    - terraform import azurerm_key_vault_secret.frontend_url_sec \
    "https://kv-weebit-prod.vault.azure.net/secrets/NextPublicFrontendUrl/f896f4d7eb64413abbcb4b27f238dd57"
    - terraform import azurerm_key_vault_secret.postgres_user "https://kv-weebit-prod.vault.azure.net/secrets/PostgresUser/cb5dc6061fde400785b0c3f44d63f159"
    - terraform import azurerm_key_vault_secret.postgres_password "https://kv-weebit-prod.vault.azure.net/secrets/PostgresPassword/5019ddb0573645529defd23fca563f9c"
    - terraform import azurerm_key_vault_secret.postgres_db "https://kv-weebit-prod.vault.azure.net/secrets/PostgresDbName/5261ca7aec0440a6aea462972d5e3fb4"
    - terraform import azurerm_key_vault_secret.postgres_port "https://kv-weebit-prod.vault.azure.net/secrets/PostgresPort/9f2dba50476f41688fc73e0fe02fd505"
    - terraform import azurerm_key_vault_secret.postgres_host "https://kv-weebit-prod.vault.azure.net/secrets/PostgresHost/dd7ac1ad94e8408da63285f54fe50308"
    - terraform import azurerm_key_vault_secret.backend_host "https://kv-weebit-prod.vault.azure.net/secrets/BackendHost/48acc972054f46258f9e2a987862ee2a"
    - terraform import azurerm_key_vault_secret.backend_port "https://kv-weebit-prod.vault.azure.net/secrets/BackendPort/b1bde9df6c2a45298d2e9e27040de40b"
    - terraform import azurerm_key_vault_secret.allowed_origins "https://kv-weebit-prod.vault.azure.net/secrets/AllowedOrigins/f30a3cd825b64100b42889801e08bfad"
    - terraform import azurerm_key_vault_secret.redis_url "https://kv-weebit-prod.vault.azure.net/secrets/RedisUrl/510fc90551a54c8a87522fff95784203"
    - terraform import azurerm_key_vault_secret.redis_port "https://kv-weebit-prod.vault.azure.net/secrets/RedisPort/997602991a794bed83b4ab75dc8da158"
    - terraform import azurerm_key_vault_secret.redis_password "https://kv-weebit-prod.vault.azure.net/secrets/RedisPassword/b17dc0943916494aa30bc1f5b6a515b0"
    - terraform import azurerm_key_vault_secret.backend_url_sec "https://kv-weebit-prod.vault.azure.net/secrets/NextPublicApiUrl/cb548e13938f47eb9be1a51688b63655"

deploy:
    terraform init
    terraform plan -out=tfplan
    terraform apply -parallelism=2 -auto-approve tfplan
    just backend-deploy
    just frontend-deploy
