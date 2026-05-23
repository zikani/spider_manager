"""
speed_limiter_dialog.py - UI for real-time global speed limit adjustment.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QSpinBox, QPushButton
)
from config import settings as app_settings

class SpeedLimiterDialog(QDialog):
    def __init__(self, parent, engine):
        super().__init__(parent)
        self._engine = engine
        self.setWindowTitle("Speed Limiter")
        self.resize(300, 150)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.limit_cb = QCheckBox("Enable Speed Limiter")
        current_limit = app_settings.get_speed_limit_kb()
        self.limit_cb.setChecked(current_limit > 0)
        layout.addWidget(self.limit_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Maximum download speed:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 999999)
        self.speed_spin.setSuffix(" KB/s")
        self.speed_spin.setValue(current_limit if current_limit > 0 else 1024)
        row.addWidget(self.speed_spin)
        layout.addLayout(row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Apply")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self):
        enabled = self.limit_cb.isChecked()
        limit_kb = self.speed_spin.value() if enabled else 0
        app_settings.set_speed_limit_kb(limit_kb)
        
        self._engine.speed_limiter.set_limit_bps(limit_kb * 1024)
        
        self.accept()
