"""Detect HTTP(S) URLs in the system clipboard (optional opt-in via settings)."""

from __future__ import annotations

import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from core.protocol_handler import UnsupportedProtocolError, normalize_url


class ClipboardMonitor(QObject):
    """Emits normalized URL strings when clipboard text looks linkable."""

    url_detected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self._last_emit = ""
        self._last_emit_time = 0.0
        self._clipboard = QGuiApplication.clipboard()
        self._clipboard.dataChanged.connect(self._queue_check)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._flush_check)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def _queue_check(self):
        if self._enabled:
            self._debounce.start()

    def _flush_check(self) -> None:
        if not self._enabled:
            return
        text = self._clipboard.text().strip()
        if not text or len(text) > 8192:
            return
        first = text.split()[0][:2048].strip()
        try:
            url = normalize_url(first)
        except (UnsupportedProtocolError, ValueError):
            return
        now = time.monotonic()
        if url == self._last_emit and (now - self._last_emit_time) < 1.5:
            return
        self._last_emit = url
        self._last_emit_time = now
        self.url_detected.emit(url)
