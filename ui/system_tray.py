"""
system_tray.py - Enhanced system tray manager for Spider Manager.
"""
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QFont, QColor
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from utils.icon_manager import icons
from resources.icons.icons import Icons

class SystemTrayManager(QObject):
    """Handles all system tray functionality including menu, notifications, and speed display."""
    
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    add_url_requested = pyqtSignal()
    pause_all_requested = pyqtSignal()
    resume_all_requested = pyqtSignal()
    show_downloads_requested = pyqtSignal()

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent = parent_window
        self._speed_mbps = 0.0
        self._active_downloads = 0
        
        self.tray_icon = QSystemTrayIcon(self.parent)
        self.tray_icon.setToolTip("Spider Manager")
        
        self._setup_menu()
        self._update_icon()
        
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _setup_menu(self):
        self.menu = QMenu()
        self.menu.setObjectName("trayMenu")
        
        # Actions
        show_action = self.menu.addAction(icons.get_icon(Icons.SPIDER_LOGO), "Show Spider Manager")
        show_action.triggered.connect(self.show_window_requested.emit)
        
        self.menu.addSeparator()
        
        add_action = self.menu.addAction(icons.get_icon(Icons.ADD), "Add URL...")
        add_action.triggered.connect(self.add_url_requested.emit)
        
        self.show_downloads_action = self.menu.addAction(icons.get_icon(Icons.DOWNLOAD), "Show Downloads")
        self.show_downloads_action.triggered.connect(self.show_downloads_requested.emit)
        self.show_downloads_action.setEnabled(False)  # Disabled when no active downloads
        
        self.menu.addSeparator()
        
        self.resume_all_action = self.menu.addAction(icons.get_icon(Icons.PLAY), "Resume All")
        self.resume_all_action.triggered.connect(self.resume_all_requested.emit)
        
        self.pause_all_action = self.menu.addAction(icons.get_icon(Icons.PAUSE), "Pause All")
        self.pause_all_action.triggered.connect(self.pause_all_requested.emit)
        
        self.menu.addSeparator()
        
        settings_action = self.menu.addAction(icons.get_icon(Icons.SETTINGS), "Settings")
        # In main_window.py we can connect this to _open_preferences
        
        exit_action = self.menu.addAction(icons.get_icon(Icons.STOP), "Exit")
        exit_action.triggered.connect(self.quit_requested.emit)
        
        self.tray_icon.setContextMenu(self.menu)

    def update_speed(self, mbps: float, active_downloads: int = 0):
        """Update the speed displayed on the tray icon badge and active downloads count."""
        if abs(self._speed_mbps - mbps) < 0.1 and mbps > 0:
            return
        self._speed_mbps = mbps
        self._active_downloads = active_downloads
        self._update_icon()
        self.tray_icon.setToolTip(f"Spider Manager - {mbps:.2f} MB/s - {active_downloads} active")
        
        # Enable/disable show downloads menu item based on active downloads
        self.show_downloads_action.setEnabled(active_downloads > 0)

    def _update_icon(self):
        # Create a base icon from spider logo
        base_pixmap = icons.get_icon(Icons.SPIDER_LOGO).pixmap(32, 32)
        
        if self._speed_mbps > 0:
            # Draw speed badge if downloading
            painter = QPainter(base_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Badge background
            painter.setBrush(QColor("#1f6feb"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(16, 16, 16, 16, 4, 4)
            
            # Badge text
            painter.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font)
            text = f"{int(self._speed_mbps)}" if self._speed_mbps < 100 else "99+"
            painter.drawText(16, 16, 16, 16, Qt.AlignmentFlag.AlignCenter, text)
            painter.end()
            
        self.tray_icon.setIcon(QIcon(base_pixmap))

    def show_notification(self, title: str, message: str, icon_type=QSystemTrayIcon.MessageIcon.Information):
        """Show a system tray notification."""
        self.tray_icon.showMessage(title, message, icon_type, 3000)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.parent.isVisible():
                self.parent.hide()
            else:
                self.show_window_requested.emit()
