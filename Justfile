set dotenv-load := true

db-up:
    docker compose up -d --wait

# Make schema changes
db-migrate env_file=".env":
    ENV_FILE={{env_file}} uv run alembic upgrade head

# Start the backend API
backend-prod: db-up (db-migrate ".env")
    ENV_FILE=.env uv run uvicorn weebit.main:app --reload --port 8080

# Run the NextJS frontend. # 22/10/2026: Yes I'll fix the 'dev' part.
frontend-prod:
    cd frontend && npm run dev 

# Run the app system, await service startup and DB migrations
[parallel]
prod: backend-prod frontend-prod
    
# Shutdown containers
down:
    docker compose down

reset:
    docker compose down -v
