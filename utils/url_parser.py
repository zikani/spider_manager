"""URL parsing helpers: validation and filename extraction.

``normalize_url`` is re-exported from :mod:`core.protocol_handler` so callers
can import it from a single canonical location without breaking existing
imports of the original.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from core.protocol_handler import (
    UnsupportedProtocolError,
    normalize_url,
)
from utils.file_utils import sanitize_filename

__all__ = [
    "UnsupportedProtocolError",
    "extract_filename",
    "is_valid_url",
    "normalize_url",
    "safe_filename_from_url",
]

_RFC5987_RE = re.compile(
    r"filename\*\s*=\s*(?P<encoding>[^']*)'(?P<lang>[^']*)'(?P<value>[^;]+)",
    re.IGNORECASE,
)
_FILENAME_RE = re.compile(
    r'filename\s*=\s*(?:"(?P<quoted>[^"]*)"|(?P<bare>[^;]+))',
    re.IGNORECASE,
)


def is_valid_url(url: str) -> bool:
    """Return ``True`` if ``url`` is a normalisable HTTP/HTTPS URL."""
    if not url:
        return False
    try:
        normalize_url(url)
    except (UnsupportedProtocolError, ValueError):
        return False
    return True


def _from_content_disposition(value: str) -> str:
    """Extract the filename from a ``Content-Disposition`` header value."""
    if not value:
        return ""
    m = _RFC5987_RE.search(value)
    if m:
        encoding = m.group("encoding") or "utf-8"
        raw = m.group("value").strip()
        try:
            return unquote(raw, encoding=encoding, errors="replace")
        except (LookupError, TypeError):
            return unquote(raw)
    m = _FILENAME_RE.search(value)
    if m:
        return (m.group("quoted") or m.group("bare") or "").strip()
    return ""


def extract_filename(url: str, headers: dict | None = None) -> str:
    """Best-effort filename for ``url``.

    Order of precedence:
        1. ``Content-Disposition`` header (RFC 5987 ``filename*`` then ``filename=``).
        2. The last URL path segment, with query string stripped and percent-decoded.
        3. ``"download"``.

    The returned name is **not** sanitised; use :func:`safe_filename_from_url`
    when writing to disk.
    """
    if headers:
        cd = headers.get("Content-Disposition") or headers.get("content-disposition") or ""
        name = _from_content_disposition(cd)
        if name:
            return name

    try:
        parsed = urlparse(url)
    except ValueError:
        return "download"

    path = parsed.path or ""
    last = path.rsplit("/", 1)[-1]
    last = unquote(last)
    if last:
        return last
    return "download"


def safe_filename_from_url(url: str, headers: dict | None = None) -> str:
    """Convenience wrapper: ``sanitize_filename(extract_filename(url, headers))``."""
    return sanitize_filename(extract_filename(url, headers))
