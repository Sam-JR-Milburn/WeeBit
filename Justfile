set dotenv-load := true

db-up:
    docker compose up -d --wait

# Make schema changes
db-migrate env_file=".env":
    PYTHONPATH=backend/src ENV_FILE={{env_file}} uv run alembic -c backend/alembic.ini upgrade head

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
    python3 -m venv antenv && \
    ./antenv/bin/pip install --upgrade pip && \
    uv export --no-hashes --format requirements-txt -o requirements.txt && \
    grep -v '^-e' requirements.txt > clean-requirements.txt && \
    ./antenv/bin/pip install -r clean-requirements.txt && \
    ./antenv/bin/pip install .

backend-deploy: backend-build
    az webapp start --resource-group rg-weebit-production --name app-weebit-api
    az webapp deploy \
    --resource-group rg-weebit-production \
    --name app-weebit-api \
    --src-path backend.zip
    --type zip

frontend-deploy:
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

deploy:
    terraform init
    terraform plan -out=tfplan
    terraform apply -parallelism=2 -auto-approve tfplan
    just backend-deploy
    just frontend-deploy
