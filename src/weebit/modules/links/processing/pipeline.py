from typing import Callable, Sequence

# Type alias for the URL normalisation functions
UrlTransformer = Callable[[str], str]

from pydantic import HttpUrl, TypeAdapter

from urllib.parse import urlsplit, urlunsplit

# 1. Strip Whitespace
def strip_whitespace(url: str) -> str:
    return url.strip()


# 2. HTTP Parsing
_url_adapter = TypeAdapter(HttpUrl)
def parse_and_validate_url(url: str) -> str:
    """
    Args:
        url: Raw URL string.
    Returns:
        str: URL parsed string.
    Raises:
        ValidationError: If the URL has an invalid scheme.
    """
    if not isinstance(url, str):
        raise TypeError("URL is not a string")

    # Can throw a ValidationError, where it will be caught and repassed as a LinkServiceError
    return str(_url_adapter.validate_python(url))


# 3. HTTP RFC 3986, lowercase scheme + hostname remove trailing port, remove trailing path
def normalise_http_scheme(url: str) -> str:
    split_url = urlsplit(url)

    scheme: str = str(split_url.scheme or "").lower()
    host: str = str(split_url.netloc or "").lower()
    port = split_url.port

    # Strip default ports.
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        netloc = host
    elif port:
        netloc = f"{host}:{port}"
    else:
        netloc = host

    # Handle username:password, if present
    if "@" in split_url.netloc:
        userinfo=split_url.netloc.split("@")[0]
        netloc=f"{userinfo}@{netloc}"

    path: str = str(split_url.path)
    if path and path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    components: tuple[str, str, str, str, str] = (
        scheme, # 'https'
        netloc, # 'google.com'
        path, # 'search'
        split_url.query, # q=project+zomboid+map
        split_url.fragment # pagesection
    )
    return urlunsplit(components)

# Optional: Order the query params alphabetically (by key)
# ----

# Optional: Remove tracking parameters
# ----

# Optional: Resolve punycode?
# ----

# Normalise the URL in order
NORMALISATION_PIPELINE: Sequence[UrlTransformer] = [
    strip_whitespace,
    parse_and_validate_url,
    normalise_http_scheme,
]
def normalise_url(
        url: str,
        pipeline: Sequence[UrlTransformer] = NORMALISATION_PIPELINE,
) -> str:
    """
    Args:
        url: the unnormalised url.
        pipeline: an ordered list of string processing functions
    Returns:
        A normalised url.
    """

    processing_url = url
    for transformer in pipeline:
        processing_url = transformer(processing_url)

    # Normalise percent-encoding and decode unreserved characters
    return str(HttpUrl(processing_url))