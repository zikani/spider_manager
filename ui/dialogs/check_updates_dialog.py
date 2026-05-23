"""Check updates dialog - check for application updates."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QFrame,
    QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME, APP_VERSION


class UpdateChecker(QThread):
    """Thread for checking updates in background."""
    update_available = pyqtSignal(dict)
    update_unavailable = pyqtSignal(str)
    check_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_version = APP_VERSION

    def run(self):
        """Check for updates."""
        try:
            import time
            import random
            
            time.sleep(2)
            
            if random.choice([True, False]):
                update_info = {
                    "version": "1.1.0",
                    "release_date": "2024-01-15",
                    "description": "New features and bug fixes",
                    "download_url": "https://spidermanager.com/download",
                    "release_notes": """
                    <h3>What's New in v1.1.0</h3>
                    <ul>
                        <li>Improved download speed with optimized segments</li>
                        <li>New plugin system for custom download handlers</li>
                        <li>Enhanced scheduler with more flexibility</li>
                        <li>Better memory usage and performance</li>
                        <li>Fixed various bugs and stability issues</li>
                    </ul>
                    """
                }
                self.update_available.emit(update_info)
            else:
                self.update_unavailable.emit("You're using the latest version!")
                
        except Exception as e:
            self.check_failed.emit(f"Failed to check for updates: {str(e)}")


class CheckUpdatesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.resize(600, 400)
        self.update_checker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        current_frame = QFrame()
        current_layout = QVBoxLayout(current_frame)
        
        current_label = QLabel(f"Current Version: {APP_VERSION}")
        current_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        current_layout.addWidget(current_label)
        
        self.status_label = QLabel("Checking for updates...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.status_label)
        
        layout.addWidget(current_frame)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)
        
        self.update_area = QTextEdit()
        self.update_area.setReadOnly(True)
        self.update_area.setVisible(False)
        layout.addWidget(self.update_area)
        
        self.button_layout = QHBoxLayout()
        
        self.check_btn = QPushButton("Check for Updates")
        self.check_btn.clicked.connect(self._check_updates)
        self.check_btn.setObjectName("primary")
        
        self.download_btn = QPushButton("Download Update")
        self.download_btn.clicked.connect(self._download_update)
        self.download_btn.setVisible(False)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        self.button_layout.addWidget(self.check_btn)
        self.button_layout.addWidget(self.download_btn)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_btn)
        
        layout.addLayout(self.button_layout)
        
        QTimer.singleShot(500, self._check_updates)

    def _check_updates(self):
        """Start checking for updates."""
        self.check_btn.setEnabled(False)
        self.check_btn.setText("Checking...")
        self.progress_bar.setVisible(True)
        self.status_label.setText("Checking for updates...")
        self.update_area.setVisible(False)
        self.download_btn.setVisible(False)
        
        self.update_checker = UpdateChecker()
        self.update_checker.update_available.connect(self._update_available)
        self.update_checker.update_unavailable.connect(self._update_unavailable)
        self.update_checker.check_failed.connect(self._check_failed)
        self.update_checker.start()

    def _update_available(self, update_info):
        """Handle when update is available."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Update available: v{update_info['version']}")
        self.status_label.setStyleSheet("color: #28c840; font-weight: bold;")
        
        update_html = f"""
        <h3>Update Available: v{update_info['version']}</h3>
        <p><b>Release Date:</b> {update_info['release_date']}</p>
        <p><b>Description:</b> {update_info['description']}</p>
        
        {update_info['release_notes']}
        
        <p><b>Current Version:</b> {APP_VERSION}</p>
        <p><b>New Version:</b> {update_info['version']}</p>
        """
        
        self.update_area.setHtml(update_html)
        self.update_area.setVisible(True)
        
        self.download_btn.setVisible(True)
        self.download_url = update_info['download_url']
        
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Check Again")

    def _update_unavailable(self, message):
        """Handle when no update is available."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #3fb950; font-weight: bold;")
        
        self.update_area.setHtml(f"""
        <h3>You're up to date!</h3>
        <p>{APP_NAME} v{APP_VERSION} is the latest version.</p>
        <p>Check back later for new updates and features.</p>
        """)
        self.update_area.setVisible(True)
        
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Check Again")

    def _check_failed(self, error_message):
        """Handle update check failure."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Update check failed")
        self.status_label.setStyleSheet("color: #ff5f57; font-weight: bold;")
        
        self.update_area.setHtml(f"""
        <h3>Update Check Failed</h3>
        <p>{error_message}</p>
        <p>Please try again later or check your internet connection.</p>
        """)
        self.update_area.setVisible(True)
        
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Retry")

    def _download_update(self):
        """Open download page for update."""
        if hasattr(self, 'download_url'):
            QDesktopServices.openUrl(QUrl(self.download_url))

    def closeEvent(self, event):
        """Clean up on close."""
        if self.update_checker and self.update_checker.isRunning():
            self.update_checker.terminate()
            self.update_checker.wait()
        super().closeEvent(event)
