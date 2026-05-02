"""Filesystem helpers: filename sanitization, unique paths, disk space."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import humanize

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_BASENAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_DEFAULT_NAME = "download"


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Return a filesystem-safe basename.

    Strips illegal characters (``<>:"/\\|?*`` and control codes), trims
    trailing dots/spaces (problematic on Windows), prefixes Windows reserved
    basenames with ``_``, and truncates to ``max_length`` characters while
    preserving the extension when possible. Falls back to ``"download"`` when
    the result would be empty.
    """
    if not name:
        return _DEFAULT_NAME

    cleaned = _ILLEGAL_CHARS.sub("_", name).strip().rstrip(". ")
    if not cleaned:
        return _DEFAULT_NAME

    stem, dot, ext = cleaned.rpartition(".")
    base_for_check = (stem if dot else cleaned).upper()
    if base_for_check in _RESERVED_BASENAMES:
        cleaned = "_" + cleaned

    if len(cleaned) > max_length:
        if dot and len(ext) < max_length - 1:
            keep = max_length - len(ext) - 1
            cleaned = (stem[:keep] if not base_for_check.startswith("_") else ("_" + stem)[:keep]) + "." + ext
        else:
            cleaned = cleaned[:max_length]

    return cleaned or _DEFAULT_NAME


def ensure_directory(path: str | Path) -> None:
    """Create ``path`` and any missing parents. No-op if it already exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def unique_path(directory: str | Path, filename: str) -> str:
    """Return a path under ``directory`` that does not collide with existing files.

    If ``directory/filename`` exists, returns ``directory/<stem> (n)<ext>`` for
    the smallest ``n >= 1`` that is free.
    """
    directory = Path(directory)
    candidate = directory / filename
    if not candidate.exists():
        return str(candidate)

    stem = candidate.stem
    suffix = candidate.suffix
    n = 1
    while True:
        candidate = directory / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return str(candidate)
        n += 1


def get_free_space(path: str | Path) -> int:
    """Return free bytes on the filesystem containing ``path``.

    Walks up to the nearest existing ancestor so it works for not-yet-created
    download directories. Returns ``0`` if the disk usage call fails.
    """
    p = Path(path)
    while not p.exists():
        parent = p.parent
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(str(p)).free
    except OSError:
        return 0


def format_size(num_bytes: int) -> str:
    """Human-readable binary size (``humanize.naturalsize`` with ``binary=True``)."""
    return humanize.naturalsize(max(0, int(num_bytes)), binary=True)
