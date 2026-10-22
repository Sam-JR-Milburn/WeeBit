from fastapi import APIRouter, Depends, Response, status, BackgroundTasks
from fastapi.responses import RedirectResponse

api_router = APIRouter(prefix="/api/link", tags=["Links API"])
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
        200: { "description": "If a short referrer code already exists for the link." },
        201: { "description": "If a new short referrer code link has been created." },
        400: { "description": "If there's been a general error in handling the link." },
        422: { "description": "If the link is non-HTTP (plaintext, 'javascript:', 'ftp://', ...) or self-referential." },
    },
    summary="Create a new short referrer link",
)
async def create_link(
    payload: schemas.LinkCreate,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache: BaseCache = Depends(get_redis)
) -> models.Link:
    """Checks if a link exists in the system, returns a short ref code if it does and creates one if it doesn't.
    Args:
        payload: The link submission object.
        response: Injected response object.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.

    Returns:
        A link object that is serialised to a LinkResponse DTO by partial projection.
    """

    link_object, created = await service.get_or_create_link(background_tasks, db, cache, payload)

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
        307: { "description": "Redirect to the stored URL if the SRC is valid." },
        404: { "description": "Yield an error if the supplied SRC doesn't exist." }
    },
)
async def redirect(
        short_referrer_code: str,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        cache: BaseCache = Depends(get_redis)
) -> RedirectResponse:
    """Ingests the short referrer code from the route and redirects if valid.
    Args:
        short_referrer_code:
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        URL redirection (on valid route input)
    """

    link_object = await service.redirect_with_src(short_referrer_code, background_tasks, db, cache)
    response = RedirectResponse(url=str(link_object.normalised_url))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return response