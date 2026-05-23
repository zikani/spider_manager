"""Changelog dialog - display version history and release notes."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QTabWidget,
    QWidget,
    QScrollArea,
    QDateEdit,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME, APP_VERSION


class ChangelogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Changelog")
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel(f"{APP_NAME} Version History")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("View version:"))
        
        self.version_combo = QComboBox()
        self._populate_versions()
        self.version_combo.currentTextChanged.connect(self._load_version)
        selector_layout.addWidget(self.version_combo)
        
        selector_layout.addStretch()
        
        current_version_btn = QPushButton("Current Version")
        current_version_btn.clicked.connect(self._show_current_version)
        selector_layout.addWidget(current_version_btn)
        
        layout.addLayout(selector_layout)
        
        self.tab_widget = QTabWidget()
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy Changelog")
        copy_btn.clicked.connect(self._copy_changelog)
        
        web_btn = QPushButton("View Online")
        web_btn.clicked.connect(self._open_online_changelog)
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(web_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self._show_current_version()

    def _populate_versions(self):
        """Populate version combo box with available versions."""
        versions = [
            "1.0.0 (Current)",
            "0.9.0 Beta",
            "0.8.0 Alpha", 
            "0.7.0 Alpha",
            "0.6.0 Alpha",
            "0.5.0 Alpha",
            "0.4.0 Alpha",
            "0.3.0 Alpha",
            "0.2.0 Alpha",
            "0.1.0 Alpha"
        ]
        
        for version in versions:
            self.version_combo.addItem(version)

    def _create_tabs(self):
        release_notes = self._create_release_notes_tab()
        self.tab_widget.addTab(release_notes, "Release Notes")
        
        features = self._create_features_tab()
        self.tab_widget.addTab(features, "Features")
        
        bugfixes = self._create_bugfixes_tab()
        self.tab_widget.addTab(bugfixes, "Bug Fixes")
        
        issues = self._create_known_issues_tab()
        self.tab_widget.addTab(issues, "Known Issues")

    def _create_release_notes_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.release_notes_content = QTextEdit()
        self.release_notes_content.setReadOnly(True)
        scroll.setWidget(self.release_notes_content)
        layout.addWidget(scroll)
        return widget

    def _create_features_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.features_content = QTextEdit()
        self.features_content.setReadOnly(True)
        scroll.setWidget(self.features_content)
        layout.addWidget(scroll)
        return widget

    def _create_bugfixes_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.bugfixes_content = QTextEdit()
        self.bugfixes_content.setReadOnly(True)
        scroll.setWidget(self.bugfixes_content)
        layout.addWidget(scroll)
        return widget

    def _create_known_issues_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.issues_content = QTextEdit()
        self.issues_content.setReadOnly(True)
        scroll.setWidget(self.issues_content)
        layout.addWidget(scroll)
        return widget

    def _show_current_version(self):
        """Show changelog for current version."""
        self.version_combo.setCurrentText("1.0.0 (Current)")
        self._load_version("1.0.0 (Current)")

    def _load_version(self, version_text):
        """Load changelog for selected version."""
        version = version_text.replace(" (Current)", "").replace(" Beta", "").replace(" Alpha", "")
        
        changelog_data = self._get_changelog_data(version)
        
        self.release_notes_content.setHtml(changelog_data["release_notes"])
        
        features_html = "<h2>New Features</h2><ul>"
        for feature in changelog_data["features"]:
            features_html += f"<li>{feature}</li>"
        features_html += "</ul>"
        self.features_content.setHtml(features_html)
        
        fixes_html = "<h2>Bug Fixes</h2><ul>"
        for fix in changelog_data["bugfixes"]:
            fixes_html += f"<li>{fix}</li>"
        fixes_html += "</ul>"
        self.bugfixes_content.setHtml(fixes_html)
        
        issues_html = "<h2>Known Issues</h2><ul>"
        for issue in changelog_data["known_issues"]:
            issues_html += f"<li>{issue}</li>"
        issues_html += "</ul>"
        self.issues_content.setHtml(issues_html)

    def _get_changelog_data(self, version):
        """Get changelog data for specific version."""
        changelog = {
            "1.0.0": {
                "release_notes": """
                <h2>Spider Manager 1.0.0 - Stable Release</h2>
                <p><b>Release Date:</b> January 15, 2024</p>
                <p><b>Type:</b> Stable Release</p>
                
                <h3>Major Highlights</h3>
                <p>This is the first stable release of Spider Manager! After extensive beta testing,
                we're excited to bring you a professional download manager with advanced features
                and a modern interface.</p>
                
                <h3>Key Improvements from Beta</h3>
                <ul>
                    <li>Improved download engine with better error handling</li>
                    <li>Enhanced user interface with refined dark theme</li>
                    <li>Optimized memory usage and performance</li>
                    <li>Comprehensive help system and documentation</li>
                    <li>Stable plugin architecture for extensibility</li>
                </ul>
                
                <h3>System Requirements</h3>
                <ul>
                    <li>Python 3.11 or higher</li>
                    <li>Windows 10/11, macOS 10.15+, or Linux</li>
                    <li>4GB RAM recommended</li>
                    <li>100MB disk space</li>
                </ul>
                """,
                "features": [
                    "Multi-segment download engine with up to 32 parallel connections",
                    "Comprehensive plugin system for media downloads",
                    "Advanced scheduler with time-based download windows",
                    "Real-time speed monitoring and bandwidth control",
                    "Modern dark theme interface with customizable options",
                    "Built-in clipboard monitoring for automatic URL detection",
                    "Category-based file organization",
                    "Batch download operations",
                    "Resume support for interrupted downloads",
                    "System tray integration for background operation",
                    "Comprehensive statistics and reporting",
                    "Cross-platform compatibility (Windows, macOS, Linux)"
                ],
                "bugfixes": [
                    "Fixed memory leak in long-running downloads",
                    "Resolved UI freezing during large file downloads",
                    "Fixed crash when handling malformed URLs",
                    "Corrected speed calculation for very fast downloads",
                    "Fixed issue with proxy authentication",
                    "Resolved problem with Unicode file names",
                    "Fixed scheduler not working on some systems",
                    "Corrected progress bar display for large files",
                    "Fixed clipboard monitor consuming excessive CPU",
                    "Resolved issue with plugin loading failures"
                ],
                "known_issues": [
                    "Some video sites may require periodic plugin updates",
                    "Very high-speed connections (>1Gbps) may show inaccurate speeds",
                    "System tray icon may not appear on some Linux desktops",
                    "Network drives may have slower performance than local storage"
                ]
            },
            "0.9.0": {
                "release_notes": """
                <h2>Spider Manager 0.9.0 - Final Beta</h2>
                <p><b>Release Date:</b> December 20, 2023</p>
                <p><b>Type:</b> Beta Release</p>
                
                <h3>Beta Phase Complete</h3>
                <p>This is the final beta release before the stable 1.0.0 version. All major
                features are implemented and we're focusing on bug fixes and polish.</p>
                """,
                "features": [
                    "Complete plugin architecture",
                    "Full scheduler implementation",
                    "Advanced bandwidth controls",
                    "Comprehensive settings system",
                    "Built-in help documentation"
                ],
                "bugfixes": [
                    "Fixed download queue corruption",
                    "Resolved UI threading issues",
                    "Fixed memory management problems",
                    "Corrected configuration saving"
                ],
                "known_issues": [
                    "Some edge cases in URL parsing",
                    "Occasional UI lag on startup",
                    "Limited video format support"
                ]
            },
            "0.8.0": {
                "release_notes": """
                <h2>Spider Manager 0.8.0 - Feature Beta</h2>
                <p><b>Release Date:</b> November 15, 2023</p>
                <p><b>Type:</b> Beta Release</p>
                
                <h3>Major Feature Update</h3>
                <p>Significant feature additions including plugin system and advanced scheduling.</p>
                """,
                "features": [
                    "Initial plugin system implementation",
                    "Basic scheduler functionality",
                    "Enhanced download engine",
                    "Improved UI responsiveness"
                ],
                "bugfixes": [
                    "Fixed download resume issues",
                    "Resolved UI freezing problems",
                    "Fixed memory leaks"
                ],
                "known_issues": [
                    "Plugin system still experimental",
                    "Scheduler limited functionality",
                    "Some UI inconsistencies"
                ]
            }
        }
        
        default_data = {
            "release_notes": f"""
            <h2>Spider Manager {version}</h2>
            <p>Release notes for version {version} are not available.</p>
            """,
            "features": ["No new features documented for this version"],
            "bugfixes": ["No bug fixes documented for this version"],
            "known_issues": ["No known issues documented for this version"]
        }
        
        return changelog.get(version, default_data)

    def _copy_changelog(self):
        """Copy current changelog to clipboard."""
        current_version = self.version_combo.currentText().replace(" (Current)", "")
        changelog_data = self._get_changelog_data(current_version.replace(" Beta", "").replace(" Alpha", ""))
        
        changelog_text = f"""{APP_NAME} Changelog - {current_version}

{changelog_data["release_notes"].replace("<h2>", "").replace("</h2>", "").replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "").replace("<h3>", "").replace("</h3>", "").replace("<ul>", "").replace("</ul>", "").replace("<li>", "• ").replace("</li>", "")}

New Features:
{chr(10).join(f"• {feature}" for feature in changelog_data["features"])}

Bug Fixes:
{chr(10).join(f"• {fix}" for fix in changelog_data["bugfixes"])}

Known Issues:
{chr(10).join(f"• {issue}" for issue in changelog_data["known_issues"])}
"""
        
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(changelog_text)
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Changelog Copied", "Changelog copied to clipboard.")

    def _open_online_changelog(self):
        """Open online changelog in browser."""
        QDesktopServices.openUrl(QUrl("https://spidermanager.com/changelog"))
