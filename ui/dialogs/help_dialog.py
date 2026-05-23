"""Help dialog - comprehensive user guide and documentation."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt

from config.constants import APP_NAME, APP_VERSION


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _create_tabs(self):
        getting_started = self._create_getting_started_tab()
        self.tab_widget.addTab(getting_started, "Getting Started")
        
        features = self._create_features_tab()
        self.tab_widget.addTab(features, "Features")
        
        shortcuts = self._create_shortcuts_tab()
        self.tab_widget.addTab(shortcuts, "Shortcuts")
        
        troubleshooting = self._create_troubleshooting_tab()
        self.tab_widget.addTab(troubleshooting, "Troubleshooting")

    def _create_getting_started_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Welcome to {app_name} v{version}</h2>
        
        <h3>Quick Start</h3>
        <ol>
            <li><b>Add Downloads:</b> Click the "Add URL" button or press Ctrl+N</li>
            <li><b>Choose Location:</b> Select where to save your files</li>
            <li><b>Start Downloading:</b> Downloads begin automatically</li>
            <li><b>Monitor Progress:</b> Watch real-time speed and progress</li>
        </ol>
        
        <h3>Adding Downloads</h3>
        <p><b>Single URL:</b> Paste or type the URL and click "Add Download"</p>
        <p><b>Multiple URLs:</b> Use "Batch Download" to add many URLs at once</p>
        <p><b>Clipboard:</b> Enable clipboard monitoring to auto-detect URLs</p>
        
        <h3>Managing Downloads</h3>
        <ul>
            <li>Right-click downloads for more options</li>
            <li>Drag to reorder queue</li>
            <li>Use categories to organize by file type</li>
            <li>Set speed limits for bandwidth control</li>
        </ul>
        
        <h3>Basic Controls</h3>
        <ul>
            <li><b>Play/Resume:</b> Start or resume paused downloads</li>
            <li><b>Pause:</b> Temporarily stop downloads</li>
            <li><b>Stop:</b> Cancel and remove downloads</li>
            <li><b>Restart:</b> Retry failed downloads</li>
        </ul>
        """.format(app_name=APP_NAME, version=APP_VERSION))
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_features_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Features Overview</h2>
        
        <h3>Download Management</h3>
        <ul>
            <li><b>Multi-segment Downloads:</b> Faster speeds with parallel connections</li>
            <li><b>Resume Support:</b> Pause and resume interrupted downloads</li>
            <li><b>Queue Management:</b> Organize and prioritize downloads</li>
            <li><b>Batch Operations:</b> Add multiple URLs simultaneously</li>
        </ul>
        
        <h3>Speed Control</h3>
        <ul>
            <li><b>Global Speed Limits:</b> Set maximum bandwidth usage</li>
            <li><b>Per-Download Limits:</b> Individual speed controls</li>
            <li><b>Scheduler:</b> Time-based download windows</li>
            <li><b>Concurrent Downloads:</b> Control simultaneous downloads</li>
        </ul>
        
        <h3>Media Support</h3>
        <ul>
            <li><b>Video Downloads:</b> YouTube, Vimeo, and more</li>
            <li><b>Audio Extraction:</b> Extract audio from videos</li>
            <li><b>Format Selection:</b> Choose quality and format</li>
            <li><b>Subtitle Support:</b> Download subtitles when available</li>
        </ul>
        
        <h3>Organization</h3>
        <ul>
            <li><b>Categories:</b> Auto-categorize by file type</li>
            <li><b>Custom Folders:</b> Set save locations per category</li>
            <li><b>Search & Filter:</b> Find downloads quickly</li>
            <li><b>Statistics:</b> Track download history and performance</li>
        </ul>
        
        <h3>Advanced Features</h3>
        <ul>
            <li><b>Plugin System:</b> Extensible download handlers</li>
            <li><b>Proxy Support:</b> Configure proxy settings</li>
            <li><b>Clipboard Monitoring:</b> Auto-detect URLs</li>
            <li><b>System Tray:</b> Background operation</li>
        </ul>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_shortcuts_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Keyboard Shortcuts</h2>
        
        <h3>File Operations</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr><th><b>Shortcut</b></th><th><b>Action</b></th></tr>
            <tr><td><code>Ctrl+N</code></td><td>Add new download</td></tr>
            <tr><td><code>Ctrl+B</code></td><td>Batch download</td></tr>
            <tr><td><code>Ctrl+O</code></td><td>Open download folder</td></tr>
            <tr><td><code>Delete</code></td><td>Remove selected downloads</td></tr>
        </table>
        
        <h3>Download Controls</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr><th><b>Shortcut</b></th><th><b>Action</b></th></tr>
            <tr><td><code>Space</code></td><td>Play/Pause selected</td></tr>
            <tr><td><code>Ctrl+P</code></td><td>Pause all downloads</td></tr>
            <tr><td><code>Ctrl+R</code></td><td>Resume all downloads</td></tr>
            <tr><td><code>Ctrl+S</code></td><td>Stop selected downloads</td></tr>
        </table>
        
        <h3>Navigation</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr><th><b>Shortcut</b></th><th><b>Action</b></th></tr>
            <tr><td><code>Ctrl+F</code></td><td>Search downloads</td></tr>
            <tr><td><code>Ctrl+1</code></td><td>Switch to All Downloads</td></tr>
            <tr><td><code>Ctrl+2</code></td><td>Switch to Downloading</td></tr>
            <tr><td><code>Ctrl+3</code></td><td>Switch to Completed</td></tr>
        </table>
        
        <h3>Application</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr><th><b>Shortcut</b></th><th><b>Action</b></th></tr>
            <tr><td><code>Ctrl+,</code></td><td>Preferences</td></tr>
            <tr><td><code>F1</code></td><td>Show help</td></tr>
            <tr><td><code>Ctrl+Q</code></td><td>Quit application</td></tr>
            <tr><td><code>F11</code></td><td>Toggle fullscreen</td></tr>
        </table>
        
        <h3>Mouse Actions</h3>
        <ul>
            <li><b>Double-click:</b> Start/pause download or open file</li>
            <li><b>Right-click:</b> Context menu with options</li>
            <li><b>Drag & Drop:</b> Add URLs from text or links</li>
            <li><b>Middle-click:</b> Open download location</li>
        </ul>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_troubleshooting_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Troubleshooting</h2>
        
        <h3>Common Issues</h3>
        
        <h4>Downloads Not Starting</h4>
        <ul>
            <li>Check internet connection</li>
            <li>Verify URL is correct and accessible</li>
            <li>Check if scheduler is preventing downloads</li>
            <li>Ensure speed limits aren't set to 0</li>
            <li>Try restarting the application</li>
        </ul>
        
        <h4>Slow Download Speeds</h4>
        <ul>
            <li>Check if speed limits are enabled</li>
            <li>Reduce concurrent downloads</li>
            <li>Try different segment count in preferences</li>
            <li>Check if proxy settings are correct</li>
            <li>Test download speed with browser</li>
        </ul>
        
        <h4>Failed Downloads</h4>
        <ul>
            <li>Check if URL is still valid</li>
            <li>Verify server allows downloading</li>
            <li>Check available disk space</li>
            <li>Try restarting failed downloads</li>
            <li>Check antivirus isn't blocking downloads</li>
        </ul>
        
        <h4>Video/Media Issues</h4>
        <ul>
            <li>Ensure yt-dlp is up to date</li>
            <li>Check if video is region-restricted</li>
            <li>Try different format selection</li>
            <li>Verify cookies are configured if needed</li>
            <li>Check if video is private or deleted</li>
        </ul>
        
        <h3>Performance Tips</h3>
        <ul>
            <li><b>Segment Count:</b> Higher values improve speed but use more connections</li>
            <li><b>Concurrent Downloads:</b> Balance between speed and system load</li>
            <li><b>Scheduler:</b> Use off-peak hours for large downloads</li>
            <li><b>Categories:</b> Organize files to avoid clutter</li>
            <li><b>Cleanup:</b> Regularly remove completed downloads</li>
        </ul>
        
        <h3>Getting Help</h3>
        <p>If you continue to experience issues:</p>
        <ul>
            <li>Check the <a href="#">online documentation</a></li>
            <li>Visit the <a href="#">support forum</a></li>
            <li>Report bugs on <a href="#">GitHub</a></li>
            <li>Contact support at support@spidermanager.com</li>
        </ul>
        
        <h3>Advanced Debugging</h3>
        <p>For technical issues, you can:</p>
        <ul>
            <li>Check log files in the application directory</li>
            <li>Enable debug mode in preferences</li>
            <li>Test with different proxy settings</li>
            <li>Verify plugin configurations</li>
        </ul>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
