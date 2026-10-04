from typing import Callable, Sequence

# Type alias for the URL normalisation functions
UrlTransformer = Callable[[str], str]

from pydantic import HttpUrl, TypeAdapter, ValidationError

from urllib.parse import urlparse, urlsplit, urlunsplit

# 1. Strip Whitespace
def strip_whitespace(url: str) -> str:
    return url.strip()

# 2. HTTP RFC 3986, lowercase scheme + hostname remove trailing port, remove trailing path
def normalise_http_scheme(url: str) -> str:
    split_url = urlsplit(url)

    scheme: str = str(split_url.scheme).lower()
    netloc: str = str(split_url.netloc).lower()

    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    elif scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]

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

# 3. Percent-Encoding Normalization

# Optional: Order the query params alphabetically (by key)
# ----

# Optional: Remove tracking parameters
# ----

# Optional: Resolve punycode?
# ----

# Normalise the URL in order
NORMALISATION_PIPELINE: Sequence[UrlTransformer] = [
    strip_whitespace,
    normalise_http_scheme,
    # Percent-Encoding Case Normalization (RFC 3986 §6.2.2.1) and
    # Unreserved Character Decoding (RFC 3986 §6.2.2.2) takes place in earlier HttpUrl parsing.
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
    return processing_url