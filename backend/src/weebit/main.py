from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from starlette.middleware import Middleware
from starlette.responses import RedirectResponse

from weebit.modules.analytics.routes import analytics_api_router
from weebit.modules.errors.routes import error_router
from weebit.modules.links.routes import links_api_router, links_redirect_router

from weebit.exceptions import ProblemException
from weebit.config import settings
from weebit.schemas import ProblemDetailResponse

from pathlib import Path
from alembic import command
from alembic.config import Config
def run_migrations():
    '''Runs the Alembic migrations on startup.'''
    sync_database_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    backend_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_dir = backend_dir / "alembic"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_database_url)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))

    command.upgrade(alembic_cfg, "head")

import asyncio
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(api: FastAPI):
    await asyncio.to_thread(run_migrations)
    yield

# Catch exceptions, reformat
def register_problem_handlers(app: FastAPI):
    @app.exception_handler(ProblemException)
    async def problem_exception_handler(request: Request, exc: ProblemException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ProblemDetailResponse(
                type=f"{settings.base_url}{exc.type_uri}",
                title=exc.title,
                status=exc.status_code,
                detail=exc.detail,
            ).model_dump(),
            media_type="application/problem+json"
        )

# Setup the API, exception handler, add the link submission and link redirection routes.
middleware = [
    Middleware(
        CORSMiddleware, # type: ignore[arg-type]
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    middleware=middleware,
    lifespan=lifespan,
)

register_problem_handlers(app)

# Order is important
app.include_router(links_api_router)
app.include_router(analytics_api_router) # /api/analytics
app.include_router(error_router) # /errors* before /{short_ref_code}
app.include_router(links_redirect_router)

@app.get("/health", tags=["Health Check Endpoint"])
async def health_check():
    return { "status": "ok" }

@app.get("/", include_in_schema=False)
async def root_to_docs():
    """Send root ('/') requests to /docs"""
    return RedirectResponse(url="/docs")