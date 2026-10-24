import hashlib
from datetime import date

from fastapi import APIRouter, Depends, Request, Response, status, BackgroundTasks
from fastapi.responses import RedirectResponse

from weebit.config import settings

links_api_router = APIRouter(prefix="/api/links", tags=["Links API"])
links_redirect_router = APIRouter(tags=["Short code redirect"])

from sqlalchemy.ext.asyncio import AsyncSession
from weebit.database import get_db

from aiocache import BaseCache
from weebit.cache import get_cache

from weebit.modules.links import schemas as links_schemas, service, models
from weebit import schemas as main_schemas

@links_api_router.post(
    path="",
    response_model=links_schemas.LinkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "If a short referrer code already exists for the link.",
            "content": {
                "application/json": {
                    "schema": links_schemas.LinkResponse.model_json_schema()
                }
            }
        },
        status.HTTP_201_CREATED: {
            "description": "If a new short referrer code link has been created.",
            "content": {
                "application/json": {
                    "schema": links_schemas.LinkResponse.model_json_schema()
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
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "If the link is non-HTTP (plaintext, 'javascript:', 'ftp://', ...) or self-referential.",
            "content": {
                "application/problem+json": {
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
    },
    summary="Create a new short referrer link",
)
async def create_link(
    payload: links_schemas.LinkCreate,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache: BaseCache = Depends(get_cache)
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



def generate_server_browser_fingerprint(request: Request) -> str:
    """
    Args:
        request: Request object that we can extract identity-correlated information
    Returns:
        64-char lower-quality browser fingerprint.
        Lacks the quality of a client-side JS fingerprint.
    """

    user_agent =            request.headers.get("user-agent", "")
    accept_language =       request.headers.get("accept-language", "")
    accept_encoding =       request.headers.get("accept-encoding", "")

    client_ip = "0.0.0.0"
    if request.client and request.client.host:
        client_ip = request.client.host

    today_salt = date.today().isoformat() # More resilient to IP address changes

    raw_signature = f"{client_ip}:{user_agent}:{accept_language}:{accept_encoding}:{today_salt}"
    return hashlib.sha256(raw_signature.encode("UTF-8")).hexdigest()

@links_redirect_router.get(
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
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "422 here is an artifact of the FastAPI route param signature. If it did fire, it would have valid shape however, due to exception catching.",
            "content": {
                "application/problem+json": {
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
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
        cache: BaseCache = Depends(get_cache)
) -> RedirectResponse:
    """Ingests the short referrer code from the route and redirects if valid.
    Args:
        short_referrer_code: A shortened string representing a stored URL.
        request: Request object - contains headers, among other items.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        URL redirection (on valid route input)
    """

    visitor_id = request.headers.get("X-Visitor-Id")
    if not visitor_id:
        visitor_id = generate_server_browser_fingerprint(request)

    link_object = await service.redirect_with_src(
        short_ref_code=short_referrer_code,
        browser_fingerprint=visitor_id, # Can't exist here without an interstitial page
        background_tasks=background_tasks,
        db=db, cache=cache)
    response = RedirectResponse(url=str(link_object.normalised_url))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return response