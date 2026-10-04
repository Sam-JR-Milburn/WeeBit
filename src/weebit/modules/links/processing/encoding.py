import hashlib

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def url_to_int256(normalised_url: str) -> int:
    """Produces a 256-bit hash of the normalised URL string.
    Args:
        normalised_url: URL input
    Returns:

    """
    digest = hashlib.sha256(normalised_url.encode("utf-8")).digest()
    return int.from_bytes(digest, byteorder="big")

SHORT_CODE_DEFAULT_LENGTH = 7
FULL_BASE62_LENGTH = 43 # 256-bit Base62 max-length.
def encode_base62(num: int, min_length: int = FULL_BASE62_LENGTH) -> str:
    """Encodes a non-negative integer into a Base62 alphanumeric string.
    Args:
        num:
        min_length:

    Returns:

    """
    if num == 0:
        return BASE62_ALPHABET[0].rjust(min_length, BASE62_ALPHABET[0])
    chars = []
    base = len(BASE62_ALPHABET)

    while num > 0:
        num, remainder = divmod(num, base)
        chars.append(BASE62_ALPHABET[remainder])

    encoded = "".join(reversed(chars))
    return encoded.rjust(min_length, BASE62_ALPHABET[0])