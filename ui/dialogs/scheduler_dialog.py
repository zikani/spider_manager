"""
scheduler_dialog.py - Time-window based download scheduler UI.
"""

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QTimeEdit, QPushButton, QGroupBox, QFormLayout
)
from config import settings as app_settings

class SchedulerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scheduler")
        self.resize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        sched_group = QGroupBox("Download Schedule")
        sched_layout = QFormLayout(sched_group)

        self.enabled_cb = QCheckBox("Enable scheduler")
        self.enabled_cb.setChecked(app_settings.get_scheduler_enabled())
        sched_layout.addRow(self.enabled_cb)

        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        start_time_str = app_settings.get_scheduler_start()
        self.start_time.setTime(QTime.fromString(start_time_str, "HH:mm") if start_time_str else QTime(9, 0))
        sched_layout.addRow("Start downloads at:", self.start_time)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        end_time_str = app_settings.get_scheduler_end()
        self.end_time.setTime(QTime.fromString(end_time_str, "HH:mm") if end_time_str else QTime(21, 0))
        sched_layout.addRow("Stop downloads at:", self.end_time)

        layout.addWidget(sched_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.hang_up = QCheckBox("Hang up modem when done")
        self.exit_app = QCheckBox("Exit Spider Manager when done")
        self.shutdown = QCheckBox("Shut down computer when done")
        options_layout.addWidget(self.hang_up)
        options_layout.addWidget(self.exit_app)
        options_layout.addWidget(self.shutdown)
        layout.addWidget(options_group)

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
        app_settings.set_scheduler_enabled(self.enabled_cb.isChecked())
        app_settings.set_scheduler_start(self.start_time.time().toString("HH:mm"))
        app_settings.set_scheduler_end(self.end_time.time().toString("HH:mm"))
        self.accept()
