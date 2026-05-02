"""Networking helpers: DNS resolution, reachability checks, proxy URLs.

The ``current_proxy`` helper reads the user's preferences and returns the
proxy URL that should be passed to ``aiohttp`` (``session.get(..., proxy=...)``).
"""

from __future__ import annotations

import os
import socket
from urllib.parse import quote


def resolve_ip(host: str, timeout: float = 3.0) -> str | None:
    """Best-effort DNS resolution for ``host``. Returns ``None`` on failure.

    The ``timeout`` argument is honoured by setting the default socket timeout
    for the duration of the call.
    """
    if not host:
        return None
    previous = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        return socket.gethostbyname(host)
    except (socket.gaierror, OSError):
        return None
    finally:
        socket.setdefaulttimeout(previous)


def is_reachable(host: str, port: int = 443, timeout: float = 3.0) -> bool:
    """TCP-connect probe. Returns ``True`` if a connection is established."""
    if not host or port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def build_proxy_url(
    host: str,
    port: int,
    user: str = "",
    password: str = "",
    scheme: str = "http",
) -> str | None:
    """Build a proxy URL like ``http://user:pass@host:port``.

    Returns ``None`` if ``host`` is empty. Username/password are URL-quoted so
    special characters don't break the URL.
    """
    if not host:
        return None
    s = (scheme or "http").lower()
    auth = ""
    if user:
        if password:
            auth = f"{quote(user, safe='')}:{quote(password, safe='')}@"
        else:
            auth = f"{quote(user, safe='')}@"
    if port and port > 0:
        return f"{s}://{auth}{host}:{int(port)}"
    return f"{s}://{auth}{host}"


def system_proxy() -> str | None:
    """Return ``HTTPS_PROXY`` or ``HTTP_PROXY`` from the environment, if set."""
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = os.environ.get(key)
        if v:
            return v
    return None


def current_proxy() -> str | None:
    """Return the active proxy URL based on user settings.

    Modes:
        - ``"none"`` -> ``None``
        - ``"system"`` -> :func:`system_proxy`
        - ``"manual"`` -> :func:`build_proxy_url` from stored host/port/credentials.
    """
    from config import settings as app_settings

    mode = app_settings.get_proxy_mode()
    if mode == "system":
        return system_proxy()
    if mode == "manual":
        return build_proxy_url(
            host=app_settings.get_proxy_host(),
            port=app_settings.get_proxy_port(),
            user=app_settings.get_proxy_user(),
            password=app_settings.get_proxy_password(),
        )
    return None
