"""Structured logging with rotating file output.

Logs go to both stderr and ``~/.spider_manager/logs/spider.log`` (rotated at
5MB, keeping 5 backups). Call :func:`setup_logging` once at application start
(idempotent) and use :func:`get_logger` from individual modules.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_HANDLER_TAG = "spider_manager"
_MAX_BYTES = 5_000_000
_BACKUP_COUNT = 5


def _log_directory() -> Path:
    return Path.home() / ".spider_manager" / "logs"


def _already_configured(root: logging.Logger) -> bool:
    return any(getattr(h, "_spider_tag", None) == _HANDLER_TAG for h in root.handlers)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with console + rotating-file handlers.

    Safe to call multiple times: subsequent calls only adjust the level and
    do not attach duplicate handlers.
    """
    root = logging.getLogger()
    root.setLevel(level)

    if _already_configured(root):
        for h in root.handlers:
            if getattr(h, "_spider_tag", None) == _HANDLER_TAG:
                h.setLevel(level)
        return

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    console._spider_tag = _HANDLER_TAG  # type: ignore[attr-defined]
    root.addHandler(console)

    try:
        log_dir = _log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "spider.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        file_handler._spider_tag = _HANDLER_TAG  # type: ignore[attr-defined]
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("Could not initialise log file: %s", e)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger. Equivalent to ``logging.getLogger`` but
    centralises the import surface so modules don't depend on the stdlib name."""
    return logging.getLogger(name)
