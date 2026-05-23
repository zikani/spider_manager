"""
downloads_window.py - Window to show active downloads when minimized to tray.
"""
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtGui import QIcon
from utils.icon_manager import icons
from resources.icons.icons import Icons
from ui.download_bridge import DownloadBridge
from core.download_engine import DownloadTask
import humanize

class DownloadsWindow(QDialog):
    """Floating window showing active downloads, accessible from system tray."""
    
    def __init__(self, parent, bridge: DownloadBridge):
        super().__init__(parent)
        self.bridge = bridge
        self.setWindowTitle("Active Downloads")
        self.setMinimumSize(600, 400)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.CustomizeWindowHint)
        
        self._setup_ui()
        self._connect_signals()
        
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_downloads)
        self._update_timer.start(1000)
        
        self._update_downloads()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Active Downloads"))
        
        close_btn = QPushButton()
        close_btn.setIcon(icons.get_icon(Icons.STOP))
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #30363d;")
        layout.addWidget(line)
        
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(5)
        self.downloads_table.setHorizontalHeaderLabels(["File", "Size", "Progress", "Speed", "ETA"])
        
        header = self.downloads_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.downloads_table.setAlternatingRowColors(True)
        self.downloads_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.downloads_table.setShowGrid(False)
        
        layout.addWidget(self.downloads_table)
        
        controls_layout = QHBoxLayout()
        
        self.pause_all_btn = QPushButton("Pause All")
        self.pause_all_btn.setIcon(icons.get_icon(Icons.PAUSE))
        self.pause_all_btn.clicked.connect(self._pause_all)
        
        self.resume_all_btn = QPushButton("Resume All")
        self.resume_all_btn.setIcon(icons.get_icon(Icons.PLAY))
        self.resume_all_btn.clicked.connect(self._resume_all)
        
        controls_layout.addWidget(self.pause_all_btn)
        controls_layout.addWidget(self.resume_all_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)

    def _pause_all(self):
        if hasattr(self.parent(), '_pause_all'):
            self.parent()._pause_all()

    def _resume_all(self):
        if hasattr(self.parent(), '_resume_all'):
            self.parent()._resume_all()


    def _connect_signals(self):
        self.bridge.tasks_changed.connect(self._update_downloads)
        self.bridge.task_progress.connect(self._update_downloads)

    @pyqtSlot()
    def _update_downloads(self):
        if hasattr(self.parent(), '_queue'):
            tasks = self.parent()._queue.tasks_snapshot()
            from core.download_engine import DownloadState
            active_tasks = [t for t in tasks if t.state in [DownloadState.QUEUED, DownloadState.DOWNLOADING, DownloadState.PAUSED]]
            
            self.downloads_table.setRowCount(len(active_tasks))
            
            for row, task in enumerate(active_tasks):
                self.downloads_table.setItem(row, 0, QTableWidgetItem(task.filename))
                
                size_text = humanize.naturalsize(task.total_size, binary=True) if task.total_size > 0 else "—"
                self.downloads_table.setItem(row, 1, QTableWidgetItem(size_text))
                
                progress_text = f"{task.progress:.1f}%"
                self.downloads_table.setItem(row, 2, QTableWidgetItem(progress_text))
                
                speed_text = humanize.naturalsize(task.speed, binary=True) + "/s" if task.speed > 0 else "—"
                self.downloads_table.setItem(row, 3, QTableWidgetItem(speed_text))
                
                eta_text = self._format_eta(task.eta) if task.eta > 0 else "—"
                self.downloads_table.setItem(row, 4, QTableWidgetItem(eta_text))
            
            has_active = len(active_tasks) > 0
            self.pause_all_btn.setEnabled(has_active)
            self.resume_all_btn.setEnabled(has_active)

    def _format_eta(self, seconds: int) -> str:
        if seconds <= 0:
            return "Unknown"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def closeEvent(self, event):
        self._update_timer.stop()
        super().closeEvent(event)
