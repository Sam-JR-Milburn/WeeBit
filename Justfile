set dotenv-load := true

# Ensure local .env exists
init-env-all:
    @test -f .env || cp .dev.env .env
init-env:
    @test -f .env || cp .env

db-up-dev: init-env-all
    docker compose --env-file dev.env up -d --wait
db-up: init-env
    docker compose up -d --wait

# Make schema changes
db-migrate:
    uv run alembic upgrade head

# Run the development app, await service startup and DB migrations
dev: db-up-dev db-migrate
    uv run uvicorn weebit.main:app --reload --port 8000

# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v