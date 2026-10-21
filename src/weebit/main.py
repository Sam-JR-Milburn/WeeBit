from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from weebit.exceptions import ProblemException
from weebit.modules.links.routes import api_router, redirect_router
from weebit.config import settings

# Catch exceptions, reformat
def register_problem_handlers(app: FastAPI):
    @app.exception_handler(ProblemException)
    async def problem_exception_handler(request: Request, exc: ProblemException):
        content = {
            "type": exc.type_uri,
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url)
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            media_type="application/problem+json"
        )

# Setup the API, exception handler, add the link submission and link redirection routes.
app = FastAPI(title=settings.PROJECT_NAME)
register_problem_handlers(app)
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
