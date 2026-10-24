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
)

register_problem_handlers(app)

# Order is important
app.include_router(links_api_router)
app.include_router(analytics_api_router) # /api/analytics
app.include_router(error_router) # /errors* before /{short_ref_code}
app.include_router(links_redirect_router)

@app.get("/health")
async def health_check():
    return { "status": "ok" }

@app.get("/", include_in_schema=False)
async def root_to_docs():
    """Send root ('/') requests to /docs"""
    return RedirectResponse(url="/docs")