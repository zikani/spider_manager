"""
download_file_info.py - Detailed add download dialog (IDM style).
"""
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QFileDialog, QFrame
)
from PyQt6.QtGui import QIcon, QPixmap
from utils.icon_manager import icons
from resources.icons.icons import Icons
from config import settings as app_settings

class DownloadFileInfoDialog(QDialog):
    def __init__(self, parent, url: str, filename: str, size_bytes: int, category: str = "General"):
        super().__init__(parent)
        self.url = url
        self.filename = filename
        self.size_bytes = size_bytes
        self.category = category
        
        self.setWindowTitle("Download File Info")
        self.setMinimumWidth(550)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # URL Row
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(self.url)
        self.url_edit.setReadOnly(True)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)

        # Category Row
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["General", "Compressed", "Documents", "Music", "Programs", "Video"])
        self.cat_combo.setCurrentText(self.category)
        cat_layout.addWidget(self.cat_combo, stretch=1)
        
        add_cat_btn = QPushButton()
        add_cat_btn.setIcon(icons.get_icon(Icons.ADD))
        add_cat_btn.setFixedSize(24, 24)
        cat_layout.addWidget(add_cat_btn)
        
        # Right Side Icon/Size
        info_side_layout = QVBoxLayout()
        self.type_icon = QLabel()
        self.type_icon.setFixedSize(48, 48)
        self._update_icon()
        info_side_layout.addWidget(self.type_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        
        import humanize
        size_text = humanize.naturalsize(self.size_bytes, binary=True) if self.size_bytes > 0 else "Unknown"
        self.size_label = QLabel(size_text)
        self.size_label.setStyleSheet("font-weight: bold; color: #58a6ff;")
        info_side_layout.addWidget(self.size_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        cat_main_layout = QHBoxLayout()
        cat_main_layout.addLayout(cat_layout, stretch=1)
        cat_main_layout.addLayout(info_side_layout)
        layout.addLayout(cat_main_layout)

        # Save As Row
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Save As:"))
        self.name_edit = QLineEdit(self.filename)
        save_layout.addWidget(self.name_edit, stretch=1)
        
        browse_btn = QPushButton()
        browse_btn.setIcon(icons.get_icon(Icons.FOLDER_OPEN))
        browse_btn.setFixedSize(30, 24)
        browse_btn.clicked.connect(self._browse)
        save_layout.addWidget(browse_btn)
        layout.addLayout(save_layout)

        # Remember checkbox
        self.remember_cb = QCheckBox(f"Remember this path for \"{self.category}\" category")
        layout.addWidget(self.remember_cb)

        # Path display (grayed out label)
        self.path_display = QLabel(app_settings.get_download_directory())
        self.path_display.setStyleSheet("color: #8b949e; background: #161b22; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.path_display)

        # Description Row
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.later_btn = QPushButton("Download Later")
        self.start_btn = QPushButton("Start Download")
        self.start_btn.setObjectName("primaryButton")
        self.cancel_btn = QPushButton("Cancel")
        
        self.start_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.later_btn.clicked.connect(lambda: self.done(2)) # Custom return code for "Later"

        btn_layout.addWidget(self.later_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _update_icon(self):
        cat = self.cat_combo.currentText()
        icon_map = {
            "Video": Icons.FILE_VIDEO,
            "Music": Icons.FILE_AUDIO,
            "Compressed": Icons.FILE_ARCHIVE,
            "Programs": Icons.SETTINGS,
            "Documents": Icons.FILE,
        }
        icon_enum = icon_map.get(cat, Icons.FILE)
        self.type_icon.setPixmap(icons.get_icon(icon_enum).pixmap(48, 48))

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder", self.path_display.text())
        if d:
            self.path_display.setText(d)

    def get_info(self):
        return {
            "filename": self.name_edit.text(),
            "save_path": self.path_display.text(),
            "category": self.cat_combo.currentText(),
            "description": self.desc_edit.text()
        }
