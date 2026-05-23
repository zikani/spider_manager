"""Tutorial dialog - interactive tutorials and learning resources."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QFrame,
    QScrollArea,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME


class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tutorial")
        self.resize(800, 600)
        self.current_step = 0
        self.tutorial_steps = self._get_tutorial_steps()
        self._setup_ui()

    def _get_tutorial_steps(self):
        """Get tutorial steps content."""
        return [
            {
                "title": "Welcome to Spider Manager",
                "content": """
                <h2>Welcome to Spider Manager!</h2>
                <p>This interactive tutorial will guide you through the basics of using Spider Manager.</p>
                
                <h3>What you'll learn:</h3>
                <ul>
                    <li>Adding and managing downloads</li>
                    <li>Using the interface effectively</li>
                    <li>Advanced features and tips</li>
                    <li>Customizing your experience</li>
                </ul>
                
                <p><b>Navigation:</b> Use the Next/Previous buttons to navigate through the tutorial.</p>
                """,
                "action": "Start Tutorial"
            },
            {
                "title": "Adding Your First Download",
                "content": """
                <h2>Adding Downloads</h2>
                <p>There are several ways to add downloads to Spider Manager:</p>
                
                <h3>Method 1: Add URL Button</h3>
                <ol>
                    <li>Click the "Add URL" button in the toolbar</li>
                    <li>Paste or type the URL</li>
                    <li>Choose save location</li>
                    <li>Click "Add Download"</li>
                </ol>
                
                <h3>Method 2: Drag & Drop</h3>
                <ul>
                    <li>Drag URLs from your browser</li>
                    <li>Drop them onto the download window</li>
                </ul>
                
                <h3>Method 3: Clipboard Monitoring</h3>
                <ul>
                    <li>Enable clipboard monitoring in preferences</li>
                    <li>Copy URLs and they'll be detected automatically</li>
                </ul>
                
                <p><b>Try it now:</b> Add a download using any of these methods!</p>
                """,
                "action": "Try Adding a Download"
            },
            {
                "title": "Understanding the Interface",
                "content": """
                <h2>The Spider Manager Interface</h2>
                
                <h3>Main Components:</h3>
                <ul>
                    <li><b>Title Bar:</b> Shows app info and window controls</li>
                    <li><b>Menu Bar:</b> Access all features and settings</li>
                    <li><b>Toolbar:</b> Quick access to common actions</li>
                    <li><b>Download List:</b> View and manage your downloads</li>
                    <li><b>Status Bar:</b> See overall statistics and status</li>
                </ul>
                
                <h3>Download List Columns:</h3>
                <ul>
                    <li><b>Name:</b> File name and icon</li>
                    <li><b>Size:</b> Total file size</li>
                    <li><b>Progress:</b> Download progress bar</li>
                    <li><b>Speed:</b> Current download speed</li>
                    <li><b>Time:</b> Estimated time remaining</li>
                    <li><b>Status:</b> Current download state</li>
                </ul>
                
                <p><b>Tip:</b> Right-click on any download for more options!</p>
                """,
                "action": "Explore the Interface"
            },
            {
                "title": "Managing Downloads",
                "content": """
                <h2>Download Management</h2>
                
                <h3>Basic Controls:</h3>
                <ul>
                    <li><b>Play/Resume:</b> Start or resume paused downloads</li>
                    <li><b>Pause:</b> Temporarily stop downloads</li>
                    <li><b>Stop:</b> Cancel and remove downloads</li>
                    <li><b>Restart:</b> Retry failed downloads</li>
                </ul>
                
                <h3>Queue Management:</h3>
                <ul>
                    <li><b>Drag to reorder:</b> Change download priority</li>
                    <li><b>Move to top/bottom:</b> Quick priority changes</li>
                    <li><b>Batch operations:</b> Control multiple downloads</li>
                </ul>
                
                <h3>Organization:</h3>
                <ul>
                    <li><b>Categories:</b> Auto-organize by file type</li>
                    <li><b>Custom folders:</b> Set save locations</li>
                    <li><b>Search & filter:</b> Find downloads quickly</li>
                </ul>
                
                <p><b>Practice:</b> Try pausing and resuming a download!</p>
                """,
                "action": "Practice Managing Downloads"
            },
            {
                "title": "Advanced Features",
                "content": """
                <h2>Advanced Features</h2>
                
                <h3>Speed Control:</h3>
                <ul>
                    <li><b>Global limits:</b> Set maximum bandwidth</li>
                    <li><b>Per-download limits:</b> Individual speed controls</li>
                    <li><b>Scheduler:</b> Time-based download windows</li>
                    <li><b>Concurrent downloads:</b> Control simultaneous tasks</li>
                </ul>
                
                <h3>Media Support:</h3>
                <ul>
                    <li><b>Video downloads:</b> YouTube, Vimeo, etc.</li>
                    <li><b>Audio extraction:</b> Get audio from videos</li>
                    <li><b>Format selection:</b> Choose quality and format</li>
                    <li><b>Subtitles:</b> Download when available</li>
                </ul>
                
                <h3>Automation:</h3>
                <ul>
                    <li><b>Clipboard monitoring:</b> Auto-detect URLs</li>
                    <li><b>Batch downloads:</b> Process multiple URLs</li>
                    <li><b>Scheduled downloads:</b> Set specific times</li>
                </ul>
                
                <p><b>Explore:</b> Check out these features in the preferences!</p>
                """,
                "action": "Explore Advanced Features"
            },
            {
                "title": "Customization and Settings",
                "content": """
                <h2>Customizing Spider Manager</h2>
                
                <h3>Preferences Categories:</h3>
                <ul>
                    <li><b>General:</b> Basic app settings and behavior</li>
                    <li><b>Bandwidth:</b> Speed limits and scheduling</li>
                    <li><b>Appearance:</b> Themes and interface options</li>
                    <li><b>Advanced:</b> Technical settings and plugins</li>
                </ul>
                
                <h3>Popular Customizations:</h3>
                <ul>
                    <li><b>Theme:</b> Choose dark or light mode</li>
                    <li><b>Download location:</b> Set default save folder</li>
                    <li><b>Speed limits:</b> Control bandwidth usage</li>
                    <li><b>Segments:</b> Optimize download speed</li>
                    <li><b>Startup options:</b> Launch behavior</li>
                </ul>
                
                <h3>Interface Tips:</h3>
                <ul>
                    <li><b>Keyboard shortcuts:</b> Use F1 for help</li>
                    <li><b>Context menus:</b> Right-click for options</li>
                    <li><b>Tool tips:</b> Hover for information</li>
                </ul>
                
                <p><b>Try it:</b> Open preferences and explore the settings!</p>
                """,
                "action": "Customize Your Settings"
            },
            {
                "title": "Tutorial Complete!",
                "content": """
                <h2>Congratulations! 🎉</h2>
                <p>You've completed the Spider Manager tutorial!</p>
                
                <h3>What you've learned:</h3>
                <ul>
                    <li>✅ Adding downloads multiple ways</li>
                    <li>✅ Understanding the interface</li>
                    <li>✅ Managing downloads effectively</li>
                    <li>✅ Using advanced features</li>
                    <li>✅ Customizing your experience</li>
                </ul>
                
                <h3>Next Steps:</h3>
                <ul>
                    <li><b>Practice:</b> Use your new skills regularly</li>
                    <li><b>Explore:</b> Try different features and settings</li>
                    <li><b>Learn more:</b> Check the help documentation</li>
                    <li><b>Join community:</b> Connect with other users</li>
                </ul>
                
                <h3>Need More Help?</h3>
                <ul>
                    <li>Press F1 for comprehensive help</li>
                    <li>Visit the online documentation</li>
                    <li>Join the community forums</li>
                    <li>Contact support for assistance</li>
                </ul>
                
                <p><b>Happy downloading with Spider Manager!</b></p>
                """,
                "action": "Finish Tutorial"
            }
        ]

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.tutorial_steps))
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat("Step %v of %m")
        layout.addWidget(self.progress_bar)
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        
        self.content_widget = QTextEdit()
        self.content_widget.setReadOnly(True)
        self.content_area.setWidget(self.content_widget)
        layout.addWidget(self.content_area)
        
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self._previous_step)
        self.prev_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next_step)
        self.next_btn.setObjectName("primary")
        
        self.action_btn = QPushButton()
        self.action_btn.clicked.connect(self._perform_action)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.action_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        self._load_step(0)

    def _load_step(self, step_index):
        """Load a specific tutorial step."""
        if 0 <= step_index < len(self.tutorial_steps):
            step = self.tutorial_steps[step_index]
            self.current_step = step_index
            
            self.title_label.setText(step["title"])
            self.content_widget.setHtml(step["content"])
            self.action_btn.setText(step["action"])
            
            self.progress_bar.setValue(step_index + 1)
            
            self.prev_btn.setEnabled(step_index > 0)
            self.next_btn.setEnabled(step_index < len(self.tutorial_steps) - 1)
            self.next_btn.setText("Finish" if step_index == len(self.tutorial_steps) - 1 else "Next")

    def _previous_step(self):
        """Go to previous tutorial step."""
        if self.current_step > 0:
            self._load_step(self.current_step - 1)

    def _next_step(self):
        """Go to next tutorial step."""
        if self.current_step < len(self.tutorial_steps) - 1:
            self._load_step(self.current_step + 1)
        else:
            self.accept()

    def _perform_action(self):
        """Perform the action for current step."""
        actions = {
            0: lambda: None,
            1: self._add_download_demo,
            2: self._explore_interface,
            3: self._manage_downloads_demo,
            4: self._explore_advanced,
            5: self._open_preferences,
            6: lambda: self.accept(),
        }
        
        if self.current_step in actions:
            actions[self.current_step]()

    def _add_download_demo(self):
        """Demo adding a download."""
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def _explore_interface(self):
        """Highlight interface elements."""
        pass

    def _manage_downloads_demo(self):
        """Demo download management."""
        pass

    def _explore_advanced(self):
        """Show advanced features."""
        pass

    def _open_preferences(self):
        """Open preferences dialog."""
        pass
