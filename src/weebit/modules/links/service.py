from typing import Tuple, Optional
from aiocache import BaseCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import BackgroundTasks

from weebit.exceptions import InvalidUrlProblem, LinkNotFoundProblem, CollisionLimitProblem, InvalidShortCodeProblem

from weebit.modules.links import schemas, models
from weebit.modules.links.processing.pipeline import normalise_url
from weebit.modules.links.processing.encoding import url_to_int256, encode_base62, SHORT_CODE_DEFAULT_LENGTH, \
    SHORT_CODE_MAX_LENGTH, VALID_CHARS

DEFAULT_CACHE_HIT_TTL = 60*5 # 5 minutes cache time on access
DEFAULT_CACHE_CREATE_TTL = 60*15 # 15 minutes cache time on creation

# Define the cache data structure
from pydantic import BaseModel
import json
class CachedLink(BaseModel):
    id: int
    url: str
    def __str__(self):
        """Serialise for caching."""
        return self.model_dump_json()
    @classmethod
    def from_cache_safe(cls, raw_data: str | None) -> Optional["CachedLink"]:
        if not raw_data:
            return None
        try:
            return cls.model_validate_json(raw_data)
        except (ValueError, TypeError):
            return None

# Background helper for analytics
from weebit.database import AsyncSessionLocal
async def background_log_task(link_id: int, event_type: models.LinkEventType, browser_fingerprint: str | None = None):

    # Do some validation on the supplied length
    valid_fingerprint = None
    if browser_fingerprint and len(browser_fingerprint) == 64:
        valid_fingerprint = browser_fingerprint

    async with AsyncSessionLocal() as session:
        analytic = models.Analytic(
            link_id=link_id,
            event_type=event_type,
            browser_fingerprint=valid_fingerprint
        )
        session.add(analytic)
        await session.commit()

async def get_or_create_link(
        payload: schemas.LinkCreate,
        browser_fingerprint: str | None,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
        cache: BaseCache,
) -> Tuple[models.Link, bool]:
    """Creates a link/short ref code pair or retrieves it if it exists.
    Args:
        payload: Link submission.
        browser_fingerprint: string (or None, if not captured) of the browser's unique fingerprint.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        A short code/link pair and whether it was created (True) or retrieved (False).
    """

    # Ingest URL, validate, normalise
    try:
        normalised_url = normalise_url(str(payload.url))
    except Exception as err:
        raise InvalidUrlProblem(detail=f"Parsing failed: {err}")

    # Convert to base62 short referrer code
    encoded: str = encode_base62(url_to_int256(normalised_url))

    # Process through collision loop (7-10)
    for length in range(SHORT_CODE_DEFAULT_LENGTH, SHORT_CODE_MAX_LENGTH):
        short_ref_code = encoded[:length]
        cache_src_key = f"src:{short_ref_code}"

        # Check cache to check if it's available
        cached_payload_raw: str | None = await cache.get(key=cache_src_key)
        cached_payload: CachedLink | None = CachedLink.from_cache_safe(cached_payload_raw)

        if cached_payload:
            if cached_payload.url == normalised_url:

                # Send analytic task to analytics worker.
                background_tasks.add_task(
                    background_log_task,
                    link_id=cached_payload.id,
                    event_type=models.LinkEventType.CREATE,
                    browser_fingerprint=browser_fingerprint,
                )

                # Cache hit - refresh TTL, return
                await cache.set(cache_src_key, str(cached_payload), ttl=DEFAULT_CACHE_HIT_TTL)
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

            # Send analytic task to analytics worker.
            background_tasks.add_task(
                background_log_task,
                link_id=new_link_obj.id,
                event_type=models.LinkEventType.CREATE,
                browser_fingerprint=browser_fingerprint,
            )

            # Store in the cache for redirects
            cache_payload = str(CachedLink(id=new_link_obj.id, url=new_link_obj.normalised_url))
            await cache.set(key=cache_src_key, value=cache_payload, ttl=DEFAULT_CACHE_CREATE_TTL)

            return new_link_obj, True

        # If it exists, we've found a collision.
        elif link_obj.normalised_url == normalised_url:

            # Send analytic task to analytics worker.
            background_tasks.add_task(
                background_log_task,
                link_id=link_obj.id,
                event_type=models.LinkEventType.CREATE,
                browser_fingerprint=browser_fingerprint,
            )

            cache_payload = str(CachedLink(id=link_obj.id, url=link_obj.normalised_url))
            await cache.set(key=cache_src_key, value=cache_payload, ttl=DEFAULT_CACHE_HIT_TTL)

            return link_obj, False

    raise CollisionLimitProblem() # Not expected to reach this in quadrillions of tries

async def redirect_with_src(
        short_ref_code: str,
        browser_fingerprint: str | None,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
        cache: BaseCache
) -> models.Link:
    """Find and return url data from a short code.
    Args:
        short_ref_code: A short string for redirection.
        browser_fingerprint: string (or None, if not captured) of the browser's unique fingerprint.
        background_tasks: Injected background task object.
        db: Injected database session.
        cache: Injected cache session.
    Returns:
        A short code/link pair
    """

    # Validate the SRC defensively.
    if not short_ref_code:
        raise LinkNotFoundProblem(short_ref_code=short_ref_code)

    if not (SHORT_CODE_DEFAULT_LENGTH <= len(short_ref_code) <= SHORT_CODE_MAX_LENGTH):
        raise InvalidShortCodeProblem(detail="Short code has an invalid format.")

    if not(all(char in VALID_CHARS for char in short_ref_code)):
        raise InvalidShortCodeProblem(detail="Short code has invalid characters.")

    # Check cache
    cache_src_key = f"src:{short_ref_code}"
    cached_payload_raw: str | None = await cache.get(key=cache_src_key)
    cached_payload: CachedLink | None = CachedLink.from_cache_safe(cached_payload_raw)
    if cached_payload:
        try:
            ttl = await cache.ttl(key=cache_src_key)
        except (AttributeError, TypeError):
            ttl = 0 # Fallback if cache backend doesn't support TTL lookup

        # Send analytic task to analytics worker.
        background_tasks.add_task(
            background_log_task,
            link_id=cached_payload.id,
            event_type=models.LinkEventType.REDIRECT,
            browser_fingerprint=browser_fingerprint,
        )

        # Set the TTL to be 5 mins if and only if the TTL is less.
        if ttl is None or ttl < DEFAULT_CACHE_HIT_TTL:
            await cache.set(cache_src_key, str(cached_payload), ttl=DEFAULT_CACHE_HIT_TTL)
        return models.Link(short_ref_code=short_ref_code, normalised_url=cached_payload.url)

    # Check db
    query = select(models.Link).where(models.Link.short_ref_code == short_ref_code)
    result = await db.execute(query)
    link_obj: models.Link | None = result.scalar_one_or_none()

    if link_obj is None:
        raise LinkNotFoundProblem(short_ref_code=short_ref_code)

    # Send analytic task to analytics worker.
    background_tasks.add_task(
        background_log_task,
        link_id=link_obj.id,
        event_type=models.LinkEventType.REDIRECT,
        browser_fingerprint=browser_fingerprint,
    )

    return link_obj