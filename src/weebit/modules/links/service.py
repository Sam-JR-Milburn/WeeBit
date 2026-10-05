from typing import Tuple
from aiocache import BaseCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from weebit.config import settings
from weebit.modules.links import schemas, models
from weebit.modules.links.processing.pipeline import normalise_url
from weebit.modules.links.processing.encoding import url_to_int256, encode_base62, SHORT_CODE_DEFAULT_LENGTH

# Generic link parsing error.
class LinkServiceError(Exception):
    pass

'''
# For links pointing at the service itself.
# Requires pre-image/hash collision - infeasible even on interstellar timelines.
class SelfReferentialLinkError(Exception):
    pass
'''

class InvalidUrlError(LinkServiceError):
    pass

# For checking URL validity
#from pydantic import HttpUrl, TypeAdapter, ValidationError
#_url_adapter = TypeAdapter(HttpUrl)

'''
def parse_and_validate_url(url: str) -> HttpUrl:
    """
    Args:
        url: Raw URL string.
    Returns:
        HttpUrl: An HttpUrl object, if the URL has a valid scheme.
    Raises:
        ValidationError: If the URL has an invalid scheme.
    """
    if not isinstance(url, str):
        raise InvalidUrlError("URL is not a string")

    try:
        return _url_adapter.validate_python(url)
    except ValidationError as vErr:
        raise InvalidUrlError(f"URL has invalid format/non-HTTP scheme: {vErr}")
'''

DEFAULT_CACHE_HIT_TTL = 60*5 # 5 minutes cache time on access
DEFAULT_CACHE_CREATE_TTL = 60*15 # 15 minutes cache time on creation

async def get_or_create_link(
        db: AsyncSession,
        cache: BaseCache,
        payload: schemas.LinkCreate
) -> Tuple[models.Link, bool]:
    """Creates a link/short ref code pair or retrieves it if it exists.
    Args:
        db: Injected database session.
        cache: Injected cache session.
        payload: Link submission.
    Returns:
        A short code/link pair and whether it was created (True) or retrieved (False).
    """

    # Ingest URL, validate, normalise
    #url = parse_and_validate_url(str(payload.url))
    try:
        normalised_url = normalise_url(str(payload.url))
    except Exception as err:
        raise LinkServiceError(f"Parsing failed: {err}")

    # Convert to base62 short referrer code
    encoded: str = encode_base62(url_to_int256(normalised_url))

    # Process through collision loop
    for length in range(SHORT_CODE_DEFAULT_LENGTH, SHORT_CODE_DEFAULT_LENGTH + 3):
        short_ref_code = encoded[:length]
        cache_src_key = f"code:{short_ref_code}"

        # Check cache to check if it's available
        cached_url: str | None = await cache.get(key=cache_src_key)
        if cached_url:
            if cached_url == normalised_url:
                # Cache hit - refresh TTL, return
                await cache.set(cache_src_key, normalised_url, ttl=DEFAULT_CACHE_HIT_TTL)
                # This is without the models.Link.id value, but it's not needed in the response DTO.
                return models.Link(short_ref_code=short_ref_code, normalised_url=normalised_url), False
            else:
                # Cache Collision! Code belongs to another URL -> try next length
                continue

        # Check db
        query = select(models.Link).where(models.Link.short_ref_code == short_ref_code)
        result = await db.execute(query)
        link_obj: models.Link | None = result.scalar_one_or_none()

        # Short Ref Code is free.
        if link_obj is None:
            new_link_obj = models.Link(
                short_ref_code=short_ref_code,
                normalised_url=normalised_url
            )
            db.add(new_link_obj)
            await db.commit()
            await db.refresh(new_link_obj)

            # Store in the cache for redirects
            await cache.set(key=cache_src_key, value=normalised_url, ttl=DEFAULT_CACHE_CREATE_TTL)
            return new_link_obj, True

        # If it exists, we've found a collision.
        elif link_obj.normalised_url == normalised_url:
            await cache.set(key=cache_src_key, value=normalised_url, ttl=DEFAULT_CACHE_HIT_TTL)
            return link_obj, False

    raise LinkServiceError("Short Code collision limit reached") # Not expected to reach this in quadrillions of tries


async def redirect_with_src(
        short_ref_code: str,
        db: AsyncSession,
        cache: BaseCache
) -> models.Link:
    """Find and return url data from a short code.
    Args:
        short_ref_code: A short string for redirection
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        A short code/link pair
    """

    # Check cache
    cache_src_key = f"code:{short_ref_code}"
    cached_url: str | None = await cache.get(key=cache_src_key)
    if cached_url:
        try:
            ttl = await cache.ttl(key=cache_src_key)
        except (AttributeError, TypeError):
            ttl = 0 # Fallback if cache backend doesn't support TTL lookup

        # Set the TTL to be 5 mins if and only if the TTL is less.
        if ttl is None or ttl < DEFAULT_CACHE_HIT_TTL:
            await cache.set(cache_src_key, cached_url, ttl=DEFAULT_CACHE_HIT_TTL)
        return models.Link(short_ref_code=short_ref_code, normalised_url=cached_url)

    # Check db
    query = select(models.Link).where(models.Link.short_ref_code == short_ref_code)
    result = await db.execute(query)
    link_obj: models.Link | None = result.scalar_one_or_none()

    if link_obj is None:
        raise LinkServiceError
    return link_obj