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

# Run the development app, await service startup and DB migrations
dev: db-up-dev (db-migrate "dev.env")
    ENV_FILE=dev.env uv run uvicorn weebit.main:app --reload --port 8080

prod: db-up (db-migrate ".env")
    ENV_FILE=.env uv run uvicorn weebit.main:app --reload --port 8080

# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v