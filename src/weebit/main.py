from fastapi import FastAPI
from weebit.modules.links.routes import api_router, redirect_router
from weebit.config import settings

# Setup the API, add the link submission and link redirection routes.
app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(api_router)
app.include_router(redirect_router)

@app.get("/health")
async def health_check():
    return { "status": "ok" }