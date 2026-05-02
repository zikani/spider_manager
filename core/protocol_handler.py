"""
HTTP/HTTPS URL validation and normalization (Phase 1). Other schemes rejected.
"""

from urllib.parse import urlparse, urlunparse


class UnsupportedProtocolError(ValueError):
    pass


def normalize_url(url: str) -> str:
    u = url.strip()
    if not u:
        raise ValueError("URL is empty")
    parsed = urlparse(u)
    if not parsed.scheme:
        u = "https://" + u
        parsed = urlparse(u)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsupportedProtocolError(f"Only HTTP and HTTPS are supported (got {scheme!r})")
    netloc = parsed.netloc.lower()
    if not netloc:
        raise ValueError("URL has no host")
    normalized = urlunparse(
        (
            scheme,
            netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return normalized
