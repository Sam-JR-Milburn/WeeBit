from fastapi import APIRouter, Depends, Response, HTTPException, status

from weebit.modules.links.models import Link

api_router = APIRouter(prefix="/api/link", tags=["Links API"])
redirect_router = APIRouter(tags=["Short code redirect"])

from sqlalchemy.ext.asyncio import AsyncSession
from weebit.database import get_db

from aiocache import BaseCache
from weebit.cache import get_redis

from weebit.modules.links import schemas, service, models


@api_router.post(
    "",
    response_model=schemas.LinkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: { "description": "If a short referrer code already exists for the link." },
        201: { "description": "If a new short referrer code link has been created." },
        400: { "description": "If there's been a general error in handling the link." },
        422: { "description": "If the link is non-HTTP (plaintext, 'javascript:', 'ftp://', ...) or self-referential." },
    }
)
async def create_link(
    payload: schemas.LinkCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: BaseCache = Depends(get_redis)
) -> models.Link:
    """Checks if a link exists in the system, returns a short ref code if it does and creates one if it doesn't.
    Args:
        payload: The link submission object.
        response: Injected response object.
        db: Injected database session.
        cache: Injected cache session.

    Returns:
        A link object that is serialised to a LinkResponse DTO by partial projection.
    Raises:
        HTTPException: If the request against the service fails to create or grab a short link.
    """

    try:
        link_object, created = await service.get_or_create_link(db, cache, payload)

        response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return link_object

    except (service.InvalidUrlError, service.SelfReferentialLinkError) as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err)
        )
    except service.LinkServiceError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )