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
