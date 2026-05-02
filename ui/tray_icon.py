"""
tray_icon.py - System tray with speed badge.
"""
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QFont, QColor
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, Qt


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super().__init__(parent)
        self._speed = 0.0
        self.setToolTip("Spider Manager")
        self._update_icon()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_icon)
        self._timer.start(2000)

        menu = QMenu()
        menu.addAction("Show").triggered.connect(parent.show)
        menu.addAction("Quit").triggered.connect(parent.close)
        self.setContextMenu(menu)

    def update_speed(self, speed_mbs: float):
        self._speed = speed_mbs
        self._update_icon()

    def _update_icon(self):
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#1f6feb"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, size - 4, size - 4)
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        text = f"{self._speed:.0f}" if self._speed > 0 else "0"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        self.setIcon(QIcon(pixmap))