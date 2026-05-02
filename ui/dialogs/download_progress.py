"""
download_progress.py - Active download status dialog (IDM style).
"""
import humanize
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QIcon
from utils.icon_manager import icons
from resources.icons.icons import Icons
from core.download_engine import DownloadTask
from ui.download_bridge import DownloadBridge

class DownloadProgressDialog(QDialog):
    def __init__(self, parent, task: DownloadTask, bridge: DownloadBridge):
        super().__init__(parent)
        self.task = task
        self.bridge = bridge
        
        self.setWindowTitle(f"{int(task.progress)}% {task.filename}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        self._setup_ui()
        
        # Connect signals
        self.bridge.task_progress.connect(self._on_progress)
        self.bridge.tasks_changed.connect(self._on_state_changed)
        
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._refresh_stats)
        self._update_timer.start(1000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Download Status
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        
        self.url_label = QLabel(self.task.url)
        self.url_label.setWordWrap(True)
        self.url_label.setStyleSheet("color: #58a6ff; font-size: 11px;")
        status_layout.addWidget(self.url_label)
        
        info_grid = QVBoxLayout()
        self.status_lbl = QLabel(f"Status: {self.task.state.name}")
        self.size_lbl = QLabel(f"File size: {humanize.naturalsize(self.task.total_size, binary=True)}")
        self.downloaded_lbl = QLabel(f"Downloaded: {humanize.naturalsize(self.task.completed_size, binary=True)} ({self.task.progress:.2f}%)")
        self.speed_lbl = QLabel(f"Transfer rate: {humanize.naturalsize(self.task.speed, binary=True)}/sec")
        self.eta_lbl = QLabel(f"Time left: {self._fmt_eta(self.task.eta)}")
        self.resume_lbl = QLabel("Resume capability: Yes")
        
        for lbl in [self.status_lbl, self.size_lbl, self.downloaded_lbl, self.speed_lbl, self.eta_lbl, self.resume_lbl]:
            lbl.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px;")
            info_grid.addWidget(lbl)
        
        status_layout.addLayout(info_grid)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.task.progress))
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #30363d;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background: #161b22;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #58a6ff);
                border-radius: 4px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        self.tabs.addTab(status_tab, "Download status")
        self.tabs.addTab(QWidget(), "Speed Limiter")
        self.tabs.addTab(QWidget(), "Options on completion")

        # Connection info section
        status_layout.addWidget(QLabel("Start positions and download progress by connections"))
        self.conn_table = QTableWidget(8, 3)
        self.conn_table.setHorizontalHeaderLabels(["N.", "Downloaded", "Info"])
        self.conn_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.conn_table.setFixedHeight(150)
        status_layout.addWidget(self.conn_table)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.details_btn = QPushButton("<< Hide details")
        self.pause_btn = QPushButton("Pause")
        self.cancel_btn = QPushButton("Cancel")
        
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.details_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _fmt_eta(self, seconds: int) -> str:
        if seconds <= 0: return "Unknown"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h {m}m {s}s"
        if m > 0: return f"{m}m {s}s"
        return f"{s} sec"

    @pyqtSlot(str)
    def _on_progress(self, tid):
        if tid == self.task.id:
            self.progress_bar.setValue(int(self.task.progress))
            self.setWindowTitle(f"{int(self.task.progress)}% {self.task.filename}")
            self._refresh_stats()

    def _refresh_stats(self):
        self.status_lbl.setText(f"Status: {self.task.state.name}")
        self.downloaded_lbl.setText(f"Downloaded: {humanize.naturalsize(self.task.completed_size, binary=True)} ({self.task.progress:.2f}%)")
        self.speed_lbl.setText(f"Transfer rate: {humanize.naturalsize(self.task.speed, binary=True)}/sec")
        self.eta_lbl.setText(f"Time left: {self._fmt_eta(self.task.eta)}")

    def _on_state_changed(self):
        # Update pause/resume button text
        from core.download_engine import DownloadState
        if self.task.state == DownloadState.PAUSED:
            self.pause_btn.setText("Resume")
        else:
            self.pause_btn.setText("Pause")

    def _toggle_pause(self):
        from core.download_engine import DownloadState
        import asyncio
        if self.task.state == DownloadState.PAUSED:
            # We would normally call self.queue.resume(self.task.id)
            # but since we don't have direct access here, we'll let the parent handle it
            # or emit a signal. For now, just a placeholder.
            pass
        else:
            pass
