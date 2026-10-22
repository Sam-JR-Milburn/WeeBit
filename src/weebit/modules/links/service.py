from typing import Tuple
from aiocache import BaseCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from weebit.exceptions import InvalidUrlProblem, LinkNotFoundProblem, CollisionLimitProblem

from weebit.modules.links import schemas, models
from weebit.modules.links.processing.pipeline import normalise_url
from weebit.modules.links.processing.encoding import url_to_int256, encode_base62, SHORT_CODE_DEFAULT_LENGTH

DEFAULT_CACHE_HIT_TTL = 60*5 # 5 minutes cache time on access
DEFAULT_CACHE_CREATE_TTL = 60*15 # 15 minutes cache time on creation

from pydantic import BaseModel
import json
class CachedLink(BaseModel):
    id: int
    url: str
    def __str__(self):
        """Serialise for caching."""
        return self.model_dump_json()

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
    try:
        normalised_url = normalise_url(str(payload.url))
    except Exception as err:
        raise InvalidUrlProblem(detail=f"Parsing failed: {err}")

    # Convert to base62 short referrer code
    encoded: str = encode_base62(url_to_int256(normalised_url))

    # Process through collision loop
    for length in range(SHORT_CODE_DEFAULT_LENGTH, SHORT_CODE_DEFAULT_LENGTH + 3):
        short_ref_code = encoded[:length]
        cache_src_key = f"code:{short_ref_code}"

        # Check cache to check if it's available
        cached_payload_raw: str | None = await cache.get(key=cache_src_key)
        cached_payload: CachedLink | None = CachedLink(**json.loads(cached_payload_raw)) if cached_payload_raw else None
        if cached_payload:
            if cached_payload.url == normalised_url:

                # Need to add an analytic event, but need to determine the link ID.
                analytic_event = models.Analytic(
                    link_id=cached_payload.id,
                    event_type=models.LinkEventType.CREATE
                )
                db.add(analytic_event)
                await db.commit()

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
            await db.flush()

            # Record analytic event for creation
            analytic_event = models.Analytic(
                link_id=new_link_obj.id, # Connects the flushed link obj automatically
                event_type=models.LinkEventType.CREATE
            )
            db.add(analytic_event)

            await db.commit()
            await db.refresh(new_link_obj)
            await db.refresh(analytic_event)

            # Store in the cache for redirects
            cache_payload = str(CachedLink(id=new_link_obj.id, url=new_link_obj.normalised_url))

            await cache.set(key=cache_src_key, value=cache_payload, ttl=DEFAULT_CACHE_CREATE_TTL)
            return new_link_obj, True

        # If it exists, we've found a collision.
        elif link_obj.normalised_url == normalised_url:
            cache_payload = str(CachedLink(id=link_obj.id, url=link_obj.normalised_url))
            await cache.set(key=cache_src_key, value=cache_payload, ttl=DEFAULT_CACHE_HIT_TTL)

            return link_obj, False

    raise CollisionLimitProblem() # Not expected to reach this in quadrillions of tries

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
    cached_payload_raw: str | None = await cache.get(key=cache_src_key)
    cached_payload: CachedLink | None = CachedLink(**json.loads(cached_payload_raw)) if cached_payload_raw else None
    if cached_payload:
        try:
            ttl = await cache.ttl(key=cache_src_key)
        except (AttributeError, TypeError):
            ttl = 0 # Fallback if cache backend doesn't support TTL lookup

        analytic_event = models.Analytic(
            link_id=cached_payload.id,
            event_type=models.LinkEventType.REDIRECT
        )
        db.add(analytic_event)
        await db.commit()

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

    # Record analytic event for access
    analytic_event = models.Analytic(
        link_id=link_obj.id,
        event_type=models.LinkEventType.REDIRECT
    )
    db.add(analytic_event)
    await db.commit()
    await db.refresh(analytic_event)

    return link_obj