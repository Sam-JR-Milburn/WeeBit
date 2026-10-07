set dotenv-load := true

# Ensure local .env exists
init-env:
    @test -f .env || cp .dev.env .env

db-up-dev: init-env
    docker compose --env-file dev.env up -d --wait
db-up: init-env
    docker compose up -d --wait

# Make schema changes
db-migrate env_file=".env":
    ENV_FILE={{env_file}} uv run alembic upgrade head

inspect-db:
    nohup beekeeper-studio >/dev/null 2>&1 &

# Start the backend API
backend-dev: db-up-dev (db-migrate "dev.env")
    ENV_FILE=dev.env uv run uvicorn weebit.main:app --reload --port 8080
backend-prod: db-up (db-migrate ".env")
    ENV_FILE=.env uv run uvicorn weebit.main:app --reload --port 8080

# Run the NextJS frontend. 
frontend-dev:
    cd frontend && npm run dev
frontend-prod:
    cd frontend && npm run dev

# Run the development app system, await service startup and DB migrations
[parallel]
dev: backend-dev frontend-dev

prod: backend-prod frontend-prod
    
# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v
