"""Map HTTP ``Content-Type`` values to Spider Manager categories.

Used to classify a download when the URL/extension alone is ambiguous, and to
fabricate a sensible extension when the server doesn't advertise a filename.
"""

from __future__ import annotations

from config.constants import category_for_filename

_DOCUMENT_SUBTYPES = {
    "pdf",
    "msword",
    "vnd.ms-excel",
    "vnd.ms-powerpoint",
    "vnd.openxmlformats-officedocument.wordprocessingml.document",
    "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "vnd.openxmlformats-officedocument.presentationml.presentation",
    "rtf",
    "epub+zip",
    "x-tex",
}
_ARCHIVE_SUBTYPES = {
    "zip",
    "x-rar-compressed",
    "vnd.rar",
    "x-7z-compressed",
    "x-tar",
    "gzip",
    "x-bzip2",
    "x-xz",
}
_PROGRAM_SUBTYPES = {
    "x-msdownload",
    "x-msi",
    "vnd.microsoft.portable-executable",
    "vnd.android.package-archive",
    "x-apple-diskimage",
    "x-debian-package",
    "x-redhat-package-manager",
}
_TEXT_SUBTYPES_AS_DOC = {"plain", "csv", "html", "xml"}

_MIME_TO_EXT = {
    "video/mp4": ".mp4",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/vnd.rar": ".rar",
    "application/x-7z-compressed": ".7z",
    "application/x-tar": ".tar",
    "application/gzip": ".gz",
    "application/x-msdownload": ".exe",
    "application/x-msi": ".msi",
    "application/vnd.android.package-archive": ".apk",
    "application/x-apple-diskimage": ".dmg",
    "application/epub+zip": ".epub",
    "application/json": ".json",
    "text/plain": ".txt",
    "text/html": ".html",
    "text/csv": ".csv",
}


def _split(content_type: str) -> tuple[str, str]:
    """Return ``(type, subtype)`` lowercased, ignoring parameters like ``; charset=...``."""
    main = (content_type or "").split(";", 1)[0].strip().lower()
    if "/" not in main:
        return "", ""
    t, s = main.split("/", 1)
    return t, s


def category_for_mime(content_type: str) -> str | None:
    """Return the Spider Manager category for ``content_type``, or ``None``."""
    t, s = _split(content_type)
    if not t:
        return None
    if t == "video":
        return "Video"
    if t == "audio":
        return "Audio"
    if t == "image":
        return "Image"
    if t == "application":
        if s in _DOCUMENT_SUBTYPES:
            return "Document"
        if s in _ARCHIVE_SUBTYPES:
            return "Archive"
        if s in _PROGRAM_SUBTYPES:
            return "Program"
    if t == "text" and s in _TEXT_SUBTYPES_AS_DOC:
        return "Document"
    return None


def category_from_metadata(filename: str, content_type: str | None) -> str:
    """Pick the best category given filename and content-type.

    Filename extension wins for known extensions (more specific than the
    server's generic ``application/octet-stream``); MIME type is used as a
    fallback. Returns ``"Other"`` if nothing matches.
    """
    by_ext = category_for_filename(filename) if filename else "Other"
    if by_ext != "Other":
        return by_ext
    if content_type:
        by_mime = category_for_mime(content_type)
        if by_mime:
            return by_mime
    return "Other"


def extension_from_mime(content_type: str) -> str:
    """Return a leading-dot extension for ``content_type``, or ``""`` if unknown."""
    main = (content_type or "").split(";", 1)[0].strip().lower()
    return _MIME_TO_EXT.get(main, "")
