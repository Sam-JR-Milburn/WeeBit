from fastapi import APIRouter, Depends, Request, Response, status, BackgroundTasks
from fastapi.responses import RedirectResponse

from weebit.config import Settings, settings

api_router = APIRouter(prefix="/api/links", tags=["Links API"])
redirect_router = APIRouter(tags=["Short code redirect"])

from sqlalchemy.ext.asyncio import AsyncSession
from weebit.database import get_db

from aiocache import BaseCache
from weebit.cache import get_redis

from weebit.modules.links import schemas, service, models

@api_router.post(
    path="",
    response_model=schemas.LinkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "If a short referrer code already exists for the link.",
            "content": {
                "application/json": {
                    "schema": schemas.LinkResponse.model_json_schema()
                }
            }
        },
        status.HTTP_201_CREATED: {
            "description": "If a new short referrer code link has been created.",
            "content": {
                "application/json": {
                    "schema": schemas.LinkResponse.model_json_schema()
                }
            },
            "headers": {
                "Location": {
                    "description": "Path to the newly created short link resource.",
                    "schema": { "type": "string", "example": "/BvIe1DV" },
                }
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "If there's been a general error in handling the link.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "If the link is non-HTTP (plaintext, 'javascript:', 'ftp://', ...) or self-referential.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
    },
    summary="Create a new short referrer link",
)
async def create_link(
    payload: schemas.LinkCreate,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache: BaseCache = Depends(get_redis)
) -> models.Link:
    """Checks if a link exists in the system, returns a short ref code if it does and creates one if it doesn't.
    Args:
        payload: The link submission object.
        request: Request object - contains headers, among other items.
        response: Injected response object.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.

    Returns:
        A link object that is serialised to a LinkResponse DTO by partial projection.
    """

    link_object, created = await service.get_or_create_link(
        payload=payload,
        browser_fingerprint=request.headers.get("X-Visitor-Id"),
        background_tasks=background_tasks,
        db=db, cache=cache)

    if created:
        response.status_code = status.HTTP_201_CREATED
        response.headers["Location"] = f"/{link_object.short_ref_code}"
    else:
        response.status_code = status.HTTP_200_OK
    return link_object

@redirect_router.get(
    path="/{short_referrer_code}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {
            "description": "Redirect to the stored URL if the SRC is valid.",
            "headers": {
                "Location": {
                    "description": "The stored URL grabbed from the short code referral.",
                    "schema": { "type": "string", "format": "uri", "example": f"{settings.base_url}/BvIe1DV" },
                },
                "Cache-Control": {
                    "description": "Prevents intermediary caching of the short code redirect.",
                    "schema": { "type": "string", "example": "no-cache, no-store, must-revalidate" },
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Yield an error if the supplied SRC doesn't exist.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "422 here is an artifact of the FastAPI route param signature. If it did fire, it would have valid shape however, due to exception catching.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
    },
    summary="Redirect to a full URL from a short referrer code"
)
async def redirect(
        short_referrer_code: str,
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        cache: BaseCache = Depends(get_redis)
) -> RedirectResponse:
    """Ingests the short referrer code from the route and redirects if valid.
    Args:
        short_referrer_code:
        request: Request object - contains headers, among other items.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        URL redirection (on valid route input)
    """

    link_object = await service.redirect_with_src(
        short_ref_code=short_referrer_code,
        browser_fingerprint=request.headers.get("X-Visitor-Id"),
        background_tasks=background_tasks,
        db=db, cache=cache)
    response = RedirectResponse(url=str(link_object.normalised_url))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return response