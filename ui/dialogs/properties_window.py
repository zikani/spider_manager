"""
properties_window.py - IDM-style download properties dialog.
Clean, professional properties window matching IDM design.
"""

import time
import humanize
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QTabWidget,
    QWidget, QTextEdit, QFrame, QScrollArea
)
from PyQt6.QtGui import QIcon, QFont
from utils.icon_manager import icons
from resources.icons.icons import Icons
from core.download_engine import DownloadTask


class PropertiesWindow(QDialog):
    """IDM-style download properties dialog."""
    
    def __init__(self, parent, task: DownloadTask):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Download Properties")
        self.setMinimumSize(500, 450)
        self.setModal(True)
        self.resize(520, 500)
        
        self.setStyleSheet("""
            QDialog {
                background-color:
                color:
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid
                background-color:
                border-top: none;
            }
            QTabBar::tab {
                background-color:
                color:
                padding: 6px 12px;
                margin-right: 1px;
                border: 1px solid
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                min-width: 70px;
                font-weight: normal;
            }
            QTabBar::tab:selected {
                background-color:
                color:
                border-bottom: 1px solid
            }
            QTabBar::tab:hover:!selected {
                background-color:
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 15px;
                background-color:
                color:
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px 0 5px;
                background-color:
            }
            QLabel {
                color:
                font-size: 11px;
            }
            QPushButton {
                background-color:
                color:
                border: 1px solid
                border-radius: 3px;
                padding: 4px 12px;
                min-width: 75px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color:
                border-color:
            }
            QPushButton:pressed {
                background-color:
            }
            QPushButton:default {
                background-color:
                color:
                border-color:
            }
            QPushButton:default:hover {
                background-color:
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup IDM-style properties dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(10, 10, 10, 10)
        general_layout.setSpacing(8)
        
        file_group = QGroupBox("File Information")
        file_layout = QGridLayout()
        file_layout.setSpacing(4)
        file_layout.setContentsMargins(8, 15, 8, 8)
        
        file_layout.addWidget(QLabel("Filename:"), 0, 0)
        self.filename_label = QLabel(self.task.filename)
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        file_layout.addWidget(self.filename_label, 0, 1)
        
        file_layout.addWidget(QLabel("URL:"), 1, 0)
        self.url_label = QLabel(self.task.url)
        self.url_label.setWordWrap(True)
        self.url_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; color: #0000ff;")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        file_layout.addWidget(self.url_label, 1, 1)
        
        file_layout.addWidget(QLabel("Save location:"), 2, 0)
        save_path = getattr(self.task, 'save_path', 'Unknown')
        self.save_path_label = QLabel(save_path)
        self.save_path_label.setWordWrap(True)
        self.save_path_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        file_layout.addWidget(self.save_path_label, 2, 1)
        
        file_group.setLayout(file_layout)
        general_layout.addWidget(file_group)
        
        progress_tab = QWidget()
        progress_layout = QVBoxLayout(progress_tab)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(8)
        
        progress_group = QGroupBox("Download Progress")
        progress_info_layout = QGridLayout()
        progress_info_layout.setSpacing(4)
        progress_info_layout.setContentsMargins(8, 15, 8, 8)
        
        progress_info_layout.addWidget(QLabel("File size:"), 0, 0)
        size_text = humanize.naturalsize(self.task.total_size, binary=True) if self.task.total_size > 0 else "Unknown"
        self.size_label = QLabel(size_text)
        self.size_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold;")
        progress_info_layout.addWidget(self.size_label, 0, 1)
        
        progress_info_layout.addWidget(QLabel("Downloaded:"), 1, 0)
        downloaded_text = humanize.naturalsize(self.task.downloaded, binary=True)
        self.downloaded_label = QLabel(downloaded_text)
        self.downloaded_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold; color: #008000;")
        progress_info_layout.addWidget(self.downloaded_label, 1, 1)
        
        progress_info_layout.addWidget(QLabel("Progress:"), 2, 0)
        progress_text = f"{self.task.progress:.2f}%"
        self.progress_label = QLabel(progress_text)
        self.progress_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold; color: #0000ff;")
        progress_info_layout.addWidget(self.progress_label, 2, 1)
        
        progress_info_layout.addWidget(QLabel("State:"), 3, 0)
        state_value = self.task.state.value if hasattr(self.task.state, 'value') else str(self.task.state)
        state_text = state_value.replace('_', ' ').title()
        self.state_label = QLabel(state_text)
        self.state_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold;")
        if state_value in ['ERROR', 'CANCELLED']:
            self.state_label.setStyleSheet(self.state_label.styleSheet() + " color: #ff0000;")
        else:
            self.state_label.setStyleSheet(self.state_label.styleSheet() + " color: #008000;")
        progress_info_layout.addWidget(self.state_label, 3, 1)
        
        progress_group.setLayout(progress_info_layout)
        progress_layout.addWidget(progress_group)
        
        speed_group = QGroupBox("Speed Information")
        speed_layout = QGridLayout()
        speed_layout.setSpacing(4)
        speed_layout.setContentsMargins(8, 15, 8, 8)
        
        speed_layout.addWidget(QLabel("Current speed:"), 0, 0)
        speed_text = humanize.naturalsize(self.task.speed, binary=True) + "/s" if self.task.speed > 0 else "0 B/s"
        self.speed_label = QLabel(speed_text)
        self.speed_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold; color: #0000ff;")
        speed_layout.addWidget(self.speed_label, 0, 1)
        
        speed_layout.addWidget(QLabel("Average speed:"), 1, 0)
        avg_speed = self._calculate_average_speed()
        avg_speed_text = humanize.naturalsize(avg_speed, binary=True) + "/s" if avg_speed > 0 else "0 B/s"
        self.avg_speed_label = QLabel(avg_speed_text)
        self.avg_speed_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        speed_layout.addWidget(self.avg_speed_label, 1, 1)
        
        speed_layout.addWidget(QLabel("Time remaining:"), 2, 0)
        eta_text = self._format_eta(self.task.eta)
        self.eta_label = QLabel(eta_text)
        self.eta_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold;")
        speed_layout.addWidget(self.eta_label, 2, 1)
        
        speed_group.setLayout(speed_layout)
        progress_layout.addWidget(speed_group)
        
        time_tab = QWidget()
        time_layout = QVBoxLayout(time_tab)
        time_layout.setContentsMargins(10, 10, 10, 10)
        time_layout.setSpacing(8)
        
        time_group = QGroupBox("Time Information")
        time_info_layout = QGridLayout()
        time_info_layout.setSpacing(4)
        time_info_layout.setContentsMargins(8, 15, 8, 8)
        
        time_info_layout.addWidget(QLabel("Added to queue:"), 0, 0)
        created_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(getattr(self.task, 'created_at', time.time()))) if hasattr(self.task, 'created_at') else "Unknown"
        self.created_label = QLabel(created_text)
        self.created_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        time_info_layout.addWidget(self.created_label, 0, 1)
        
        time_info_layout.addWidget(QLabel("Download started:"), 1, 0)
        started_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.task.started_at)) if self.task.started_at else "Not started"
        self.started_label = QLabel(started_text)
        self.started_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        time_info_layout.addWidget(self.started_label, 1, 1)
        
        time_info_layout.addWidget(QLabel("Completed:"), 2, 0)
        completed_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.task.completed_at)) if self.task.completed_at else "Not completed"
        self.completed_label = QLabel(completed_text)
        self.completed_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        time_info_layout.addWidget(self.completed_label, 2, 1)
        
        time_info_layout.addWidget(QLabel("Duration:"), 3, 0)
        duration_text = self._calculate_duration()
        self.duration_label = QLabel(duration_text)
        self.duration_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold;")
        time_info_layout.addWidget(self.duration_label, 3, 1)
        
        time_group.setLayout(time_info_layout)
        time_layout.addWidget(time_group)
        
        technical_tab = QWidget()
        technical_layout = QVBoxLayout(technical_tab)
        technical_layout.setContentsMargins(10, 10, 10, 10)
        technical_layout.setSpacing(8)
        
        technical_group = QGroupBox("Technical Details")
        technical_info_layout = QGridLayout()
        technical_info_layout.setSpacing(4)
        technical_info_layout.setContentsMargins(8, 15, 8, 8)
        
        technical_info_layout.addWidget(QLabel("Task ID:"), 0, 0)
        self.id_label = QLabel(self.task.id)
        self.id_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-family: monospace;")
        technical_info_layout.addWidget(self.id_label, 0, 1)
        
        technical_info_layout.addWidget(QLabel("Category:"), 1, 0)
        category_text = getattr(self.task, 'category', 'Uncategorized')
        self.category_label = QLabel(category_text)
        self.category_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        technical_info_layout.addWidget(self.category_label, 1, 1)
        
        technical_info_layout.addWidget(QLabel("Segments:"), 2, 0)
        segments_count = len(getattr(self.task, 'segments', []))
        self.segments_label = QLabel(str(segments_count))
        self.segments_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px;")
        technical_info_layout.addWidget(self.segments_label, 2, 1)
        
        technical_info_layout.addWidget(QLabel("Resume support:"), 3, 0)
        resume_text = "Yes" if getattr(self.task, 'supports_resume', True) else "No"
        self.resume_label = QLabel(resume_text)
        self.resume_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold;")
        if resume_text == "Yes":
            self.resume_label.setStyleSheet(self.resume_label.styleSheet() + " color: #008000;")
        else:
            self.resume_label.setStyleSheet(self.resume_label.styleSheet() + " color: #ff0000;")
        technical_info_layout.addWidget(self.resume_label, 3, 1)
        
        technical_group.setLayout(technical_info_layout)
        technical_layout.addWidget(technical_group)
        
        self.tabs.addTab(general_tab, "General")
        self.tabs.addTab(progress_tab, "Progress")
        self.tabs.addTab(time_tab, "Time")
        self.tabs.addTab(technical_tab, "Technical")
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 8, 0, 0)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(icons.get_icon(Icons.DOWNLOAD))
        self.refresh_btn.clicked.connect(self._refresh_data)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setIcon(icons.get_icon(Icons.STOP))
        self.close_btn.setDefault(True)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _calculate_average_speed(self) -> float:
        """Calculate average download speed."""
        if not self.task.started_at or self.task.downloaded == 0:
            return 0.0
            
        current_time = time.time()
        elapsed_time = current_time - self.task.started_at
        
        if elapsed_time <= 0:
            return 0.0
            
        return self.task.downloaded / elapsed_time
    
    def _format_eta(self, seconds: int) -> str:
        """Format ETA in human readable format."""
        if seconds <= 0:
            return "Unknown"
        if seconds < 60:
            return f"{seconds}s"
        m, s = divmod(seconds, 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        if h < 24:
            return f"{h}h {m}m"
        d, h = divmod(h, 24)
        return f"{d}d {h}h"
    
    def _calculate_duration(self) -> str:
        """Calculate download duration."""
        if not self.task.started_at:
            return "Not started"
            
        if self.task.completed_at:
            duration = self.task.completed_at - self.task.started_at
        elif self.task.state.value in ['DOWNLOADING', 'PAUSED'] if hasattr(self.task.state, 'value') else str(self.task.state) in ['DOWNLOADING', 'PAUSED']:
            duration = time.time() - self.task.started_at
        else:
            return "N/A"
            
        if duration <= 0:
            return "0s"
            
        if duration < 60:
            return f"{int(duration)}s"
        m, s = divmod(int(duration), 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        if h < 24:
            return f"{h}h {m}m"
        d, h = divmod(h, 24)
        return f"{d}d {h}h"
    
    @pyqtSlot()
    def _refresh_data(self):
        """Refresh the displayed data."""
        size_text = humanize.naturalsize(self.task.total_size, binary=True) if self.task.total_size > 0 else "Unknown"
        self.size_label.setText(size_text)
        
        downloaded_text = humanize.naturalsize(self.task.downloaded, binary=True)
        self.downloaded_label.setText(downloaded_text)
        
        progress_text = f"{self.task.progress:.2f}%"
        self.progress_label.setText(progress_text)
        
        state_value = self.task.state.value if hasattr(self.task.state, 'value') else str(self.task.state)
        state_text = state_value.replace('_', ' ').title()
        self.state_label.setText(state_text)
        if state_value in ['ERROR', 'CANCELLED']:
            self.state_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold; color: #ff0000;")
        else:
            self.state_label.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; padding: 2px 4px; font-weight: bold; color: #008000;")
        
        speed_text = humanize.naturalsize(self.task.speed, binary=True) + "/s" if self.task.speed > 0 else "0 B/s"
        self.speed_label.setText(speed_text)
        
        avg_speed = self._calculate_average_speed()
        avg_speed_text = humanize.naturalsize(avg_speed, binary=True) + "/s" if avg_speed > 0 else "0 B/s"
        self.avg_speed_label.setText(avg_speed_text)
        
        eta_text = self._format_eta(self.task.eta)
        self.eta_label.setText(eta_text)
        
        duration_text = self._calculate_duration()
        self.duration_label.setText(duration_text)
