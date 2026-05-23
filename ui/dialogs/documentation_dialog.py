"""Documentation dialog - links to online documentation and resources."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME


class DocumentationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Documentation")
        self.resize(700, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel(f"{APP_NAME} Documentation")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h3>Online Documentation</h3>
        <p>Access comprehensive documentation and guides online:</p>
        
        <h4>📚 User Guides</h4>
        <ul>
            <li><a href="#">Getting Started Guide</a> - Learn the basics</li>
            <li><a href="#">Advanced Features</a> - Power user guide</li>
            <li><a href="#">Configuration Guide</a> - Settings and preferences</li>
            <li><a href="#">Plugin Development</a> - Create custom plugins</li>
        </ul>
        
        <h4>🔧 Technical Documentation</h4>
        <ul>
            <li><a href="#">API Reference</a> - Developer documentation</li>
            <li><a href="#">Configuration Options</a> - All settings explained</li>
            <li><a href="#">Command Line Interface</a> - CLI usage</li>
            <li><a href="#">Integration Guide</a> - Third-party integrations</li>
        </ul>
        
        <h4>📖 Tutorials</h4>
        <ul>
            <li><a href="#">Video Tutorials</a> - Visual learning</li>
            <li><a href="#">Step-by-Step Guides</a> - Detailed walkthroughs</li>
            <li><a href="#">Best Practices</a> - Optimize your workflow</li>
            <li><a href="#">Troubleshooting Guide</a> - Common solutions</li>
        </ul>
        
        <h4>🌐 Community Resources</h4>
        <ul>
            <li><a href="#">Wiki</a> - Community-maintained knowledge base</li>
            <li><a href="#">FAQ</a> - Frequently asked questions</li>
            <li><a href="#">Forums</a> - Community discussions</li>
            <li><a href="#">Blog</a> - Tips and announcements</li>
        </ul>
        
        <h3>Offline Resources</h3>
        <p>Documentation available within the application:</p>
        <ul>
            <li><b>Help → User Guide</b> - Built-in help system</li>
            <li><b>Context Help</b> - F1 for contextual assistance</li>
            <li><b>Tool Tips</b> - Hover over UI elements</li>
        </ul>
        
        <h3>Documentation Formats</h3>
        <p>Documentation available in multiple formats:</p>
        <ul>
            <li><b>Web:</b> Always up-to-date online version</li>
            <li><b>PDF:</b> Printable documentation</li>
            <li><b>eBook:</b> Mobile-friendly format</li>
            <li><b>Markdown:</b> Developer-friendly source</li>
        </ul>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        
        online_btn = QPushButton("Open Online Docs")
        online_btn.clicked.connect(self._open_online_docs)
        
        pdf_btn = QPushButton("Download PDF")
        pdf_btn.clicked.connect(self._download_pdf)
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(online_btn)
        button_layout.addWidget(pdf_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _open_online_docs(self):
        """Open online documentation in browser."""
        QDesktopServices.openUrl(QUrl("https://spidermanager.com/docs"))

    def _download_pdf(self):
        """Download PDF documentation."""
        QDesktopServices.openUrl(QUrl("https://spidermanager.com/docs/pdf"))
