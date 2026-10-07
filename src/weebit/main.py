from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from weebit.modules.links.routes import api_router, redirect_router
from weebit.config import settings

# Setup the API, add the link submission and link redirection routes.
app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(api_router)
app.include_router(redirect_router)

@app.get("/health")
async def health_check():
    return { "status": "ok" }
    
# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
