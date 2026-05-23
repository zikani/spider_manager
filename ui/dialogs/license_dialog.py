"""License dialog - display software license and legal information."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME, APP_VERSION, APP_AUTHOR


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("License")
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel(f"{APP_NAME} License Information")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        self.tab_widget = QTabWidget()
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy License")
        copy_btn.clicked.connect(self._copy_license)
        
        download_btn = QPushButton("Download License")
        download_btn.clicked.connect(self._download_license)
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(download_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _create_tabs(self):
        mit_license = self._create_mit_license_tab()
        self.tab_widget.addTab(mit_license, "MIT License")
        
        third_party = self._create_third_party_tab()
        self.tab_widget.addTab(third_party, "Third Party Licenses")
        
        usage_terms = self._create_usage_terms_tab()
        self.tab_widget.addTab(usage_terms, "Usage Terms")
        
        privacy = self._create_privacy_tab()
        self.tab_widget.addTab(privacy, "Privacy Policy")

    def _create_mit_license_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
        <h2>MIT License</h2>
        
        <p>Copyright (c) 2024 {APP_AUTHOR}</p>
        
        <p>Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:</p>
        
        <p>The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.</p>
        
        <p>THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.</p>
        
        <h3>What This Means</h3>
        <ul>
            <li><b>Freedom to Use:</b> You can use {APP_NAME} for any purpose</li>
            <li><b>Freedom to Modify:</b> You can modify the source code</li>
            <li><b>Freedom to Distribute:</b> You can share copies with others</li>
            <li><b>Freedom to Study:</b> You can examine how it works</li>
            <li><b>No Warranty:</b> The software is provided "as is"</li>
            <li><b>No Liability:</b> Authors are not liable for damages</li>
        </ul>
        
        <h3>Attribution</h3>
        <p>If you use {APP_NAME} or its code in your own projects, please keep the
        copyright notice and license text intact.</p>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_third_party_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml("""
        <h2>Third Party Licenses</h2>
        
        <p>{APP_NAME} uses the following third-party libraries and components:</p>
        
        <h3>PyQt6 (Riverbank Computing)</h3>
        <p><b>License:</b> GPL v3</p>
        <p><b>Website:</b> <a href="#">https://www.riverbankcomputing.com/software/pyqt/</a></p>
        <p><b>Description:</b> Python bindings for Qt framework</p>
        
        <h3>qasync (HarHarLinks)</h3>
        <p><b>License:</b> BSD 2-Clause</p>
        <p><b>Website:</b> <a href="#">https://github.com/har-har/qasync</a></p>
        <p><b>Description:</b> Asyncio integration for PyQt</p>
        
        <h3>aiohttp (aio-libs)</h3>
        <p><b>License:</b> Apache 2.0</p>
        <p><b>Website:</b> <a href="#">https://aiohttp.readthedocs.io/</a></p>
        <p><b>Description:</b> Async HTTP client/server</p>
        
        <h3>aiofiles (Tinche)</h3>
        <p><b>License:</b> Apache 2.0</p>
        <p><b>Website:</b> <a href="#">https://github.com/Tinche/aiofiles</a></p>
        <p><b>Description:</b> Async file operations</p>
        
        <h3>yt-dlp (yt-dlp)</h3>
        <p><b>License:</b> Unlicense</p>
        <p><b>Website:</b> <a href="#">https://github.com/yt-dlp/yt-dlp</a></p>
        <p><b>Description:</b> YouTube/media downloader</p>
        
        <h3>pyperclip (asweigart)</h3>
        <p><b>License:</b> BSD</p>
        <p><b>Website:</b> <a href="#">https://github.com/asweigart/pyperclip</a></p>
        <p><b>Description:</b> Cross-platform clipboard access</p>
        
        <h3>psutil (giampaolo)</h3>
        <p><b>License:</b> BSD 3-Clause</p>
        <p><b>Website:</b> <a href="#">https://psutil.readthedocs.io/</a></p>
        <p><b>Description:</b> System and process utilities</p>
        
        <h3>humanize (jmoiron)</h3>
        <p><b>License:</b> MIT</p>
        <p><b>Website:</b> <a href="#">https://github.com/jmoiron/humanize</a></p>
        <p><b>Description:</b> Human readable data formatting</p>
        
        <h3>Icons and Assets</h3>
        <p><b>License:</b> Custom/CC BY 4.0</p>
        <p><b>Description:</b> Custom icons and UI elements</p>
        
        <h3>License Compatibility</h3>
        <p>All third-party libraries used in {APP_NAME} have licenses compatible with
        the MIT license and allow for commercial use, modification, and distribution.</p>
        
        <h3>Source Code</h3>
        <p>Source code for all third-party dependencies can be found in the
        application's dependencies or on their respective websites.</p>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_usage_terms_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
        <h2>Usage Terms and Conditions</h2>
        
        <h3>Acceptance of Terms</h3>
        <p>By using {APP_NAME}, you agree to comply with these terms and conditions.</p>
        
        <h3>Permitted Uses</h3>
        <ul>
            <li><b>Personal Use:</b> Use {APP_NAME} for personal, non-commercial purposes</li>
            <li><b>Commercial Use:</b> Use {APP_NAME} for commercial purposes</li>
            <li><b>Educational Use:</b> Use {APP_NAME} for educational and teaching purposes</li>
            <li><b>Modification:</b> Modify the software for your own use</li>
            <li><b>Distribution:</b> Share copies with others, maintaining license terms</li>
        </ul>
        
        <h3>Restrictions</h3>
        <ul>
            <li><b>No Warranty:</b> Software is provided "as is" without warranty</li>
            <li><b>No Liability:</b> Authors not liable for damages or data loss</li>
            <li><b>Compliance:</b> Must comply with applicable laws and regulations</li>
            <li><b>Copyright:</b> Must respect copyright and intellectual property</li>
            <li><b>No Reverse Engineering:</b> For security circumvention purposes</li>
        </ul>
        
        <h3>Download Responsibilities</h3>
        <p>Users are responsible for:</p>
        <ul>
            <li>Ensuring they have rights to download content</li>
            <li>Complying with terms of service of content providers</li>
            <li>Respecting copyright and intellectual property laws</li>
            <li>Using downloaded content legally and ethically</li>
        </ul>
        
        <h3>Privacy and Data</h3>
        <ul>
            <li>{APP_NAME} does not collect personal information without consent</li>
            <li>Download history is stored locally on your device</li>
            <li>No data is transmitted to third parties without permission</li>
            <li>Users control their data and can delete it at any time</li>
        </ul>
        
        <h3>Updates and Support</h3>
        <ul>
            <li>Updates are provided on an "as available" basis</li>
            <li>No guaranteed support or maintenance is provided</li>
            <li>Community support may be available through forums</li>
            <li>Bug reports and feature requests are welcome</li>
        </ul>
        
        <h3>Termination</h3>
        <p>This license is effective until terminated. Your rights under this license
        will terminate automatically if you fail to comply with any of its terms.</p>
        
        <h3>Changes to Terms</h3>
        <p>We reserve the right to modify these terms at any time. Continued use of
        {APP_NAME} constitutes acceptance of any changes.</p>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _create_privacy_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
        <h2>Privacy Policy</h2>
        
        <h3>Information We Collect</h3>
        <p>{APP_NAME} is designed to respect your privacy. We collect:</p>
        
        <h4>Local Data Only</h4>
        <ul>
            <li><b>Download History:</b> URLs, file names, and download status</li>
            <li><b>Settings:</b> User preferences and configuration</li>
            <li><b>Statistics:</b> Local download statistics and performance data</li>
            <li><b>Temporary Files:</b> Download segments and cache files</li>
        </ul>
        
        <h4>No Remote Collection</h4>
        <ul>
            <li>No personal information is sent to our servers</li>
            <li>No download URLs are transmitted externally</li>
            <li>No usage analytics or tracking</li>
            <li>No telemetry data collection</li>
        </ul>
        
        <h3>How We Use Information</h3>
        <ul>
            <li><b>Download Management:</b> To manage and organize downloads</li>
            <li><b>User Preferences:</b> To remember your settings</li>
            <li><b>Performance:</b> To optimize download speed and reliability</li>
            <li><b>Features:</b> To provide application functionality</li>
        </ul>
        
        <h3>Data Storage</h3>
        <ul>
            <li>All data is stored locally on your device</li>
            <li>No data is stored in cloud services</li>
            <li>You have full control over your data</li>
            <li>Data can be exported or deleted at any time</li>
        </ul>
        
        <h3>Third-Party Services</h3>
        <p>{APP_NAME} may interact with third-party services:</p>
        <ul>
            <li><b>Content Providers:</b> When downloading from websites</li>
            <li><b>Update Checks:</b> When checking for application updates</li>
            <li><b>Plugin Services:</b> When using third-party plugins</li>
        </ul>
        
        <p>These interactions are governed by the respective service's privacy policies.</p>
        
        <h3>Your Rights</h3>
        <ul>
            <li><b>Access:</b> You can access all your stored data</li>
            <li><b>Correction:</b> You can modify or update your data</li>
            <li><b>Deletion:</b> You can delete any or all data</li>
            <li><b>Export:</b> You can export your data for backup</li>
            <li><b>Portability:</b> You can move data between devices</li>
        </ul>
        
        <h3>Data Security</h3>
        <p>We protect your data by:</p>
        <ul>
            <li>Storing data locally on your device</li>
            <li>Using secure connections for downloads</li>
            <li>Not transmitting sensitive data externally</li>
            <li>Following security best practices</li>
        </ul>
        
        <h3>Children's Privacy</h3>
        <p>{APP_NAME} is not directed to children under 13. We do not knowingly
        collect personal information from children under 13.</p>
        
        <h3>Changes to Privacy Policy</h3>
        <p>We may update this privacy policy from time to time. We will notify
        users of any material changes.</p>
        
        <h3>Contact Information</h3>
        <p>If you have questions about this privacy policy, please contact us at:
        privacy@spidermanager.com</p>
        """)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def _copy_license(self):
        """Copy license text to clipboard."""
        license_text = f"""{APP_NAME} v{APP_VERSION}

MIT License

Copyright (c) 2024 {APP_AUTHOR}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
        
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(license_text)
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "License Copied", "License text copied to clipboard.")

    def _download_license(self):
        """Download license file."""
        QDesktopServices.openUrl(QUrl("https://spidermanager.com/license"))
