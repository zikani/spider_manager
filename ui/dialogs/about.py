"""About dialog with enhanced features and system information."""

import sys
import platform
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QScrollArea,
    QTabWidget,
    QWidget,
    QApplication,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QPixmap

from config.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_AUTHOR, APP_URL
from utils.icon_manager import icons
from resources.icons.icons import Icons


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.resize(600, 500)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy System Info")
        copy_btn.clicked.connect(self._copy_system_info)
        
        updates_btn = QPushButton("Check for Updates")
        updates_btn.clicked.connect(self._check_updates)
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(updates_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _create_tabs(self):
        about_tab = self._create_about_tab()
        self.tab_widget.addTab(about_tab, "About")
        
        system_tab = self._create_system_tab()
        self.tab_widget.addTab(system_tab, "System")
        
        credits_tab = self._create_credits_tab()
        self.tab_widget.addTab(credits_tab, "Credits")

    def _create_about_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_pixmap = icons.get_icon(Icons.SPIDER_LOGO).pixmap(64, 64)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_layout = QVBoxLayout()
        
        title_label = QLabel(f"<h2>{APP_NAME}</h2>")
        title_label.setStyleSheet("color: #58a6ff; font-weight: bold;")
        
        version_label = QLabel(f"<h3>Version {APP_VERSION}</h3>")
        version_label.setStyleSheet("color: #8b949e;")
        
        desc_label = QLabel(APP_DESCRIPTION)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 10px 0;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(version_label)
        info_layout.addWidget(desc_label)
        info_layout.addStretch()
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        links_frame = QFrame()
        links_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        links_layout = QVBoxLayout(links_frame)
        
        links_label = QLabel("<b>Links:</b>")
        links_layout.addWidget(links_label)
        
        website_btn = QPushButton("🌐 Official Website")
        website_btn.setStyleSheet("text-align: left; padding: 8px;")
        website_btn.clicked.connect(self._open_website)
        links_layout.addWidget(website_btn)
        
        docs_btn = QPushButton("📚 Documentation")
        docs_btn.setStyleSheet("text-align: left; padding: 8px;")
        docs_btn.clicked.connect(self._open_documentation)
        links_layout.addWidget(docs_btn)
        
        source_btn = QPushButton("💻 Source Code")
        source_btn.setStyleSheet("text-align: left; padding: 8px;")
        source_btn.clicked.connect(self._open_source)
        links_layout.addWidget(source_btn)
        
        issue_btn = QPushButton("🐛 Report Issue")
        issue_btn.setStyleSheet("text-align: left; padding: 8px;")
        issue_btn.clicked.connect(self._report_issue)
        links_layout.addWidget(issue_btn)
        
        layout.addWidget(links_frame)
        layout.addStretch()

    def _create_system_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(self._get_system_info())
        info_text.setFont(QFont("Consolas", 9))
        
        scroll.setWidget(info_text)
        layout.addWidget(scroll)
        
        return widget

    def _create_credits_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Credits</h2>
        
        <h3>Development Team</h3>
        <p><b>Spider Manager Team</b><br>
        Lead developers, UI/UX design, and core functionality</p>
        
        <h3>Technologies Used</h3>
        <ul>
            <li><b>Python 3.11+</b> - Core programming language</li>
            <li><b>PyQt6</b> - GUI framework</li>
            <li><b>aiohttp</b> - Async HTTP client</li>
            <li><b>asyncio</b> - Async programming</li>
            <li><b>yt-dlp</b> - Media extraction</li>
        </ul>
        
        <h3>Third-Party Libraries</h3>
        <ul>
            <li><b>qasync</b> - Qt-asyncio integration</li>
            <li><b>aiofiles</b> - Async file operations</li>
            <li><b>pyperclip</b> - Clipboard monitoring</li>
            <li><b>psutil</b> - System information</li>
            <li><b>humanize</b> - Human-readable formatting</li>
        </ul>
        
        <h3>Icons and Assets</h3>
        <p>Custom icon set designed for Spider Manager with modern, clean aesthetics.</p>
        
        <h3>Acknowledgments</h3>
        <p>Special thanks to the open-source community and PyQt developers for making this project possible.</p>
        
        <h3>License</h3>
        <p>This software is released under the MIT License. See the License dialog for full details.</p>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _get_system_info(self):
        """Collect system information."""
        info = []
        
        info.append(f"Python Version: {sys.version}")
        info.append(f"Python Implementation: {sys.implementation.name}")
        
        info.append(f"Operating System: {platform.system()} {platform.release()}")
        info.append(f"Architecture: {platform.machine()}")
        info.append(f"Processor: {platform.processor()}")
        
        qt_version = QApplication.instance().applicationVersion()
        info.append(f"Qt Version: {qt_version}")
        
        from PyQt6 import QtCore
        info.append(f"PyQt6 Version: {QtCore.QT_VERSION_STR}")
        info.append(f"PyQt6 Runtime Version: {QtCore.PYQT_VERSION_STR}")
        
        info.append(f"Application Name: {APP_NAME}")
        info.append(f"Application Version: {APP_VERSION}")
        info.append(f"Application Path: {sys.executable}")
        
        info.append(f"Working Directory: {sys.path[0]}")
        
        return "\n".join(info)

    def _copy_system_info(self):
        """Copy system information to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._get_system_info())

    def _open_website(self):
        """Open official website."""
        QDesktopServices.openUrl(QUrl(APP_URL))

    def _open_documentation(self):
        """Open documentation."""
        QDesktopServices.openUrl(QUrl(f"{APP_URL}/docs"))

    def _open_source(self):
        """Open source code repository."""
        QDesktopServices.openUrl(QUrl(f"{APP_URL}/source"))

    def _report_issue(self):
        """Open issue tracker."""
        QDesktopServices.openUrl(QUrl(f"{APP_URL}/issues"))

    def _check_updates(self):
        """Check for application updates."""
        from ui.dialogs.check_updates_dialog import CheckUpdatesDialog
        CheckUpdatesDialog(self).exec()
