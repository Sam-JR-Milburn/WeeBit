from typing import Tuple
from aiocache import BaseCache
from sqlalchemy.ext.asyncio import AsyncSession

from weebit.config import Settings
from weebit.modules.links import schemas, models
from weebit.modules.links.pipeline import normalise_url

# Generic link parsing error.
class LinkServiceError(Exception):
    pass

# For links pointing at the service itself.
class SelfReferentialLinkError(Exception):
    pass

class InvalidUrlError(LinkServiceError):
    pass

# For checking URL validity
from pydantic import HttpUrl, TypeAdapter, ValidationError
_url_adapter = TypeAdapter(HttpUrl)

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

def assert_url_not_self_referential(url: HttpUrl) -> None:
    """
    Returns:
        Whether the submitted link points to the link shortener service itself.
        Can cause infinite redirect - arrested by most modern browsers.
    """
    host = url.host
    if not host:
        return
    url_host: str = host.lower()
    self_hostname = Settings.HOSTNAME.lower()

    if url_host == self_hostname or url_host.endswith(f".{self_hostname}"):
        raise SelfReferentialLinkError(f"Can't shorten URLs pointing to the service domain: {self_hostname}")

async def get_or_create_link(
        db: AsyncSession,
        cache: BaseCache,
        payload: schemas.LinkCreate
) -> Tuple[models.Link, bool]:
    """
    Args:
        db: Injected database session.
        cache: Injected cache session.
        payload: Link submission.
    Returns:
        A short code/link pair and whether it was created (True) or retrieved (False).
    """

    # Ingest URL, validate, normalise
    url = parse_and_validate_url(str(payload.url))
    assert_url_not_self_referential(url)
    try:
        normalised_url = normalise_url(str(url))
    except:
        raise LinkServiceError("Parsing failed.")

    # Convert to base62 short referrer code
    # ----
    print(normalised_url)


    # Check if it's in the cache, return normalised link if it is

    # Check if it's in the DB, return normalised link if it is

    return (None, False)