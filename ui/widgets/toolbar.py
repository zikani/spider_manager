"""
toolbar.py - Main action toolbar.
"""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QToolBar, QWidget, QHBoxLayout, QLineEdit, QLabel, QSizePolicy
from PyQt6.QtGui import QAction, QIcon
from utils.icon_manager import icons
from resources.icons.icons import Icons


class DownloadToolbar(QToolBar):
    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.setIconSize(QSize(16, 16))

        self.action_add_url = self.add_button("Add URL", icon=icons.get_icon(Icons.ADD), is_primary=True)
        self.action_batch = self.add_button("Batch", icon=icons.get_icon(Icons.DOWNLOAD_ALL))

        self.addSeparator()
        self.action_resume = self.add_button("Resume", icon=icons.get_icon(Icons.PLAY))
        self.action_pause = self.add_button("Pause", icon=icons.get_icon(Icons.PAUSE))
        self.action_cancel = self.add_button("Cancel", icon=icons.get_icon(Icons.STOP))

        self.addSeparator()
        self.action_delete = self.add_button("Delete", icon=icons.get_icon(Icons.DELETE))
        self.action_open_folder = self.add_button("Open Folder", icon=icons.get_icon(Icons.FOLDER_OPEN))

        self.addSeparator()
        self.action_settings = self.add_button("Settings", icon=icons.get_icon(Icons.SETTINGS))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)
        lbl = QLabel("⌕")
        lbl.setStyleSheet("color: #8b949e; font-size: 14px;")
        search_layout.addWidget(lbl)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search downloads...")
        self.search_input.setStyleSheet(
            "background: #0d1117; border: 1px solid #30363d; border-radius: 6px; "
            "padding: 4px 10px; color: #e6edf3;"
        )
        self.search_input.setFixedWidth(140)
        search_layout.addWidget(self.search_input)
        self.addWidget(search_container)

    def add_button(self, text, icon=None, is_primary=False):
        action = QAction(text, self)
        if icon:
            action.setIcon(icon)
        if is_primary:
            action.setObjectName("primaryButton")
        self.addAction(action)
        return action
