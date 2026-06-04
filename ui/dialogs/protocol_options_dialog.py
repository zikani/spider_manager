"""
Protocol Options Dialog - Protocol-specific download options
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QGroupBox,
    QPushButton,
    QTabWidget,
    QWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from utils.icon_manager import icons
from resources.icons.icons import Icons


class ProtocolOptionsDialog(QDialog):
    """Protocol-specific download options dialog"""
    
    def __init__(self, protocol: str, parent=None):
        super().__init__(parent)
        self.protocol = protocol.lower()
        self.setup_ui()
        self.setWindowTitle(f"{protocol.upper()} Options")
        self.setWindowIcon(icons.get_icon(Icons.SPIDER_LOGO))
        self.resize(500, 400)
    
    def setup_ui(self):
        """Setup protocol-specific options"""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different protocol options
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add protocol-specific tab
        if self.protocol == 'ftp':
            self.setup_ftp_tab()
        elif self.protocol in ['torrent', 'magnet']:
            self.setup_torrent_tab()
        else:
            self.setup_http_tab()
        
        # Add common options tab
        self.setup_common_tab()
        
        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def setup_ftp_tab(self):
        """FTP-specific options (auth, mode, etc.)"""
        ftp_widget = QWidget()
        ftp_layout = QVBoxLayout(ftp_widget)
        
        # Authentication group
        auth_group = QGroupBox("Authentication")
        auth_layout = QVBoxLayout()
        
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.ftp_username = QLineEdit()
        self.ftp_username.setPlaceholderText("Leave empty for anonymous")
        username_layout.addWidget(self.ftp_username)
        auth_layout.addLayout(username_layout)
        
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.ftp_password = QLineEdit()
        self.ftp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.ftp_password.setPlaceholderText("Leave empty for anonymous")
        password_layout.addWidget(self.ftp_password)
        auth_layout.addLayout(password_layout)
        
        auth_group.setLayout(auth_layout)
        ftp_layout.addWidget(auth_group)
        
        # Connection mode group
        mode_group = QGroupBox("Connection Mode")
        mode_layout = QVBoxLayout()
        
        self.ftp_passive = QCheckBox("Use Passive Mode")
        self.ftp_passive.setChecked(True)
        self.ftp_passive.setToolTip("Passive mode is more firewall-friendly")
        mode_layout.addWidget(self.ftp_passive)
        
        self.ftp_tls = QCheckBox("Use FTPS (FTP over TLS)")
        self.ftp_tls.setChecked(False)
        self.ftp_tls.setToolTip("Encrypt FTP connection with TLS")
        mode_layout.addWidget(self.ftp_tls)
        
        mode_group.setLayout(mode_layout)
        ftp_layout.addWidget(mode_group)
        
        # Timeout settings
        timeout_group = QGroupBox("Timeout Settings")
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Connection Timeout (seconds):"))
        self.ftp_timeout = QSpinBox()
        self.ftp_timeout.setRange(5, 300)
        self.ftp_timeout.setValue(30)
        timeout_layout.addWidget(self.ftp_timeout)
        timeout_layout.addStretch()
        timeout_group.setLayout(timeout_layout)
        ftp_layout.addWidget(timeout_group)
        
        ftp_layout.addStretch()
        self.tabs.addTab(ftp_widget, "FTP")
    
    def setup_torrent_tab(self):
        """Torrent-specific options (seeding, peers, etc.)"""
        torrent_widget = QWidget()
        torrent_layout = QVBoxLayout(torrent_widget)
        
        # Connection settings
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QVBoxLayout()
        
        max_connections_layout = QHBoxLayout()
        max_connections_layout.addWidget(QLabel("Max Connections:"))
        self.torrent_max_connections = QSpinBox()
        self.torrent_max_connections.setRange(1, 500)
        self.torrent_max_connections.setValue(50)
        max_connections_layout.addWidget(self.torrent_max_connections)
        max_connections_layout.addStretch()
        connection_layout.addLayout(max_connections_layout)
        
        max_upload_slots_layout = QHBoxLayout()
        max_upload_slots_layout.addWidget(QLabel("Max Upload Slots:"))
        self.torrent_max_upload_slots = QSpinBox()
        self.torrent_max_upload_slots.setRange(1, 100)
        self.torrent_max_upload_slots.setValue(8)
        max_upload_slots_layout.addWidget(self.torrent_max_upload_slots)
        max_upload_slots_layout.addStretch()
        connection_layout.addLayout(max_upload_slots_layout)
        
        connection_group.setLayout(connection_layout)
        torrent_layout.addWidget(connection_group)
        
        # Speed limits
        speed_group = QGroupBox("Speed Limits")
        speed_layout = QVBoxLayout()
        
        download_limit_layout = QHBoxLayout()
        download_limit_layout.addWidget(QLabel("Download Limit (KB/s, 0 = unlimited):"))
        self.torrent_download_limit = QSpinBox()
        self.torrent_download_limit.setRange(0, 100000)
        self.torrent_download_limit.setValue(0)
        self.torrent_download_limit.setSpecialValueText("Unlimited")
        download_limit_layout.addWidget(self.torrent_download_limit)
        download_limit_layout.addStretch()
        speed_layout.addLayout(download_limit_layout)
        
        upload_limit_layout = QHBoxLayout()
        upload_limit_layout.addWidget(QLabel("Upload Limit (KB/s, 0 = unlimited):"))
        self.torrent_upload_limit = QSpinBox()
        self.torrent_upload_limit.setRange(0, 100000)
        self.torrent_upload_limit.setValue(0)
        self.torrent_upload_limit.setSpecialValueText("Unlimited")
        upload_limit_layout.addWidget(self.torrent_upload_limit)
        upload_limit_layout.addStretch()
        speed_layout.addLayout(upload_limit_layout)
        
        speed_group.setLayout(speed_layout)
        torrent_layout.addWidget(speed_group)
        
        # Seeding settings
        seeding_group = QGroupBox("Seeding Settings")
        seeding_layout = QVBoxLayout()
        
        seed_ratio_layout = QHBoxLayout()
        seed_ratio_layout.addWidget(QLabel("Seed Ratio (0 = don't seed):"))
        self.torrent_seed_ratio = QDoubleSpinBox()
        self.torrent_seed_ratio.setRange(0.0, 100.0)
        self.torrent_seed_ratio.setValue(0.0)
        self.torrent_seed_ratio.setSingleStep(0.1)
        self.torrent_seed_ratio.setSpecialValueText("Don't seed")
        seed_ratio_layout.addWidget(self.torrent_seed_ratio)
        seed_ratio_layout.addStretch()
        seeding_layout.addLayout(seed_ratio_layout)
        
        seed_time_layout = QHBoxLayout()
        seed_time_layout.addWidget(QLabel("Seed Time Limit (minutes, 0 = unlimited):"))
        self.torrent_seed_time = QSpinBox()
        self.torrent_seed_time.setRange(0, 10080)  # Up to 1 week
        self.torrent_seed_time.setValue(0)
        self.torrent_seed_time.setSpecialValueText("Unlimited")
        seed_time_layout.addWidget(self.torrent_seed_time)
        seed_time_layout.addStretch()
        seeding_layout.addLayout(seed_time_layout)
        
        seeding_group.setLayout(seeding_layout)
        torrent_layout.addWidget(seeding_group)
        
        # Download options
        download_options_group = QGroupBox("Download Options")
        download_options_layout = QVBoxLayout()
        
        self.torrent_sequential = QCheckBox("Sequential Download")
        self.torrent_sequential.setToolTip("Download pieces in order for preview")
        self.torrent_sequential.setChecked(False)
        download_options_layout.addWidget(self.torrent_sequential)
        
        self.torrent_prioritize = QCheckBox("Prioritize First and Last Pieces")
        self.torrent_prioritize.setToolTip("Download first and last pieces first for preview")
        self.torrent_prioritize.setChecked(True)
        download_options_layout.addWidget(self.torrent_prioritize)
        
        download_options_group.setLayout(download_options_layout)
        torrent_layout.addWidget(download_options_group)
        
        torrent_layout.addStretch()
        self.tabs.addTab(torrent_widget, "Torrent")
    
    def setup_http_tab(self):
        """HTTP-specific options"""
        http_widget = QWidget()
        http_layout = QVBoxLayout(http_widget)
        
        info_label = QLabel(
            "HTTP/HTTPS downloads use the global settings from Preferences.\n"
            "No protocol-specific options are available."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        http_layout.addWidget(info_label)
        http_layout.addStretch()
        
        self.tabs.addTab(http_widget, "HTTP")
    
    def setup_common_tab(self):
        """Common options for all protocols"""
        common_widget = QWidget()
        common_layout = QVBoxLayout(common_widget)
        
        info_label = QLabel(
            "Common download options are configured in the main Preferences dialog.\n"
            "This tab is reserved for future common protocol options."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        common_layout.addWidget(info_label)
        common_layout.addStretch()
        
        self.tabs.addTab(common_widget, "Common")
    
    def get_ftp_options(self) -> dict:
        """Get FTP options from dialog"""
        return {
            'username': self.ftp_username.text() or None,
            'password': self.ftp_password.text() or None,
            'passive': self.ftp_passive.isChecked(),
            'use_tls': self.ftp_tls.isChecked(),
            'timeout': self.ftp_timeout.value(),
        }
    
    def get_torrent_options(self) -> dict:
        """Get torrent options from dialog"""
        return {
            'max_connections': self.torrent_max_connections.value(),
            'max_upload_slots': self.torrent_max_upload_slots.value(),
            'download_limit': self.torrent_download_limit.value(),
            'upload_limit': self.torrent_upload_limit.value(),
            'seed_ratio': self.torrent_seed_ratio.value(),
            'seed_time': self.torrent_seed_time.value() * 60,  # Convert to seconds
            'sequential': self.torrent_sequential.isChecked(),
            'prioritize_first_last': self.torrent_prioritize.isChecked(),
        }
    
    def get_options(self) -> dict:
        """Get all options for current protocol"""
        if self.protocol == 'ftp':
            return {'ftp': self.get_ftp_options()}
        elif self.protocol in ['torrent', 'magnet']:
            return {'torrent': self.get_torrent_options()}
        else:
            return {}
    
    def set_ftp_options(self, options: dict):
        """Set FTP options in dialog"""
        self.ftp_username.setText(options.get('username', ''))
        self.ftp_password.setText(options.get('password', ''))
        self.ftp_passive.setChecked(options.get('passive', True))
        self.ftp_tls.setChecked(options.get('use_tls', False))
        self.ftp_timeout.setValue(options.get('timeout', 30))
    
    def set_torrent_options(self, options: dict):
        """Set torrent options in dialog"""
        self.torrent_max_connections.setValue(options.get('max_connections', 50))
        self.torrent_max_upload_slots.setValue(options.get('max_upload_slots', 8))
        self.torrent_download_limit.setValue(options.get('download_limit', 0))
        self.torrent_upload_limit.setValue(options.get('upload_limit', 0))
        self.torrent_seed_ratio.setValue(options.get('seed_ratio', 0.0))
        self.torrent_seed_time.setValue(options.get('seed_time', 0) // 60)  # Convert to minutes
        self.torrent_sequential.setChecked(options.get('sequential', False))
        self.torrent_prioritize.setChecked(options.get('prioritize_first_last', True))
    
    def set_options(self, options: dict):
        """Set options for current protocol"""
        if self.protocol == 'ftp':
            self.set_ftp_options(options.get('ftp', {}))
        elif self.protocol in ['torrent', 'magnet']:
            self.set_torrent_options(options.get('torrent', {}))
    
    def validate_and_accept(self):
        """Validate options and accept dialog if valid"""
        if self.protocol == 'ftp':
            if not self.validate_ftp_options():
                return
        elif self.protocol in ['torrent', 'magnet']:
            if not self.validate_torrent_options():
                return
        
        self.accept()
    
    def validate_ftp_options(self) -> bool:
        """Validate FTP options"""
        # Check if username is provided without password
        username = self.ftp_username.text()
        password = self.ftp_password.text()
        
        if username and not password:
            reply = QMessageBox.question(
                self,
                "FTP Authentication",
                "You provided a username but no password. Continue with anonymous password?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return False
        
        # Check timeout value
        if self.ftp_timeout.value() < 5:
            QMessageBox.warning(
                self,
                "Invalid Timeout",
                "Connection timeout must be at least 5 seconds."
            )
            return False
        
        return True
    
    def validate_torrent_options(self) -> bool:
        """Validate torrent options"""
        # Check connection limits
        if self.torrent_max_connections.value() < 1:
            QMessageBox.warning(
                self,
                "Invalid Connections",
                "Max connections must be at least 1."
            )
            return False
        
        if self.torrent_max_upload_slots.value() < 1:
            QMessageBox.warning(
                self,
                "Invalid Upload Slots",
                "Max upload slots must be at least 1."
            )
            return False
        
        # Check if both seed ratio and seed time are 0 (no seeding)
        if (self.torrent_seed_ratio.value() == 0.0 and 
            self.torrent_seed_time.value() == 0):
            reply = QMessageBox.question(
                self,
                "No Seeding",
                "You have disabled seeding. This may harm the torrent swarm. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return False
        
        return True
