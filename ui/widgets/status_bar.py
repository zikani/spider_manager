"""
status_bar.py - Speed, active count, disk space.
"""

from datetime import datetime

import humanize
import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout


class DownloadStatusBar(QStatusBar):
    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)

        self._dl_label = QLabel("0 downloading")
        self._ps_label = QLabel("0 paused")
        self._ok_label = QLabel("0 completed")

        self.addWidget(self._make_indicator("#58a6ff", self._dl_label))
        self.addWidget(self._make_indicator("#d29922", self._ps_label))
        self.addWidget(self._make_indicator("#3fb950", self._ok_label))

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        self.speed_label = QLabel("↓ 0 B/s")
        self.speed_label.setStyleSheet("color: #8b949e;")
        self.disk_label = QLabel("")
        self.disk_label.setStyleSheet("color: #8b949e;")
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #8b949e;")

        right_layout.addWidget(self.speed_label)
        right_layout.addWidget(self.disk_label)
        right_layout.addWidget(self.time_label)
        self.addPermanentWidget(right_widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time_disk)
        self.timer.start(1000)
        self._update_time_disk()

    def _make_indicator(self, color, text_label: QLabel):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QWidget()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {color}; border-radius: 3px;")
        text_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(dot)
        layout.addWidget(text_label)
        return widget

    def update_stats(self, stats: dict, download_path: str | None = None) -> None:
        self._dl_label.setText(f"{stats.get('active', 0)} downloading")
        self._ps_label.setText(f"{stats.get('paused', 0)} paused")
        self._ok_label.setText(f"{stats.get('completed', 0)} completed")
        spd = float(stats.get("total_speed", 0) or 0)
        self.speed_label.setText(
            f"↓ {humanize.naturalsize(spd, binary=True)}/s"
            if spd > 0
            else "↓ 0 B/s"
        )
        self._download_path = download_path

    def _update_time_disk(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
        path = getattr(self, "_download_path", None) or ""
        try:
            if path:
                usage = psutil.disk_usage(path)
            else:
                usage = psutil.disk_usage("/")
            self.disk_label.setText(
                f"💾 Disk free: {humanize.naturalsize(usage.free, binary=True)}"
            )
        except Exception:
            self.disk_label.setText("💾 Disk: —")
