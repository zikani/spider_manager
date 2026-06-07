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
from utils.file_categorizer import FileCategorizer, DownloadPathManager

class DownloadFileInfoDialog(QDialog):
    def __init__(self, parent, url: str, filename: str, size_bytes: int, category: str = None):
        super().__init__(parent)
        self.url = url
        self.filename = filename
        self.size_bytes = size_bytes
        self.selected_directory = ""
        self.protocol = self._detect_protocol(url)
        self.protocol_options = {}
        
        if category is None:
            detected_category = FileCategorizer.categorize_by_extension(filename)
            category_map = {
                "Programs": "Programs",
                "Documents": "Documents",
                "Compressed": "Compressed",
                "Pictures": "Pictures",
                "Video": "Video",
                "Audio": "Music",
                "Other": "General"
            }
            # Auto-detect torrent category for magnet/torrent URLs
            if self.protocol in ["magnet", "torrent"]:
                self.category = "Torrents"
            else:
                self.category = category_map.get(detected_category, "General")
        else:
            self.category = category
        
        self.setWindowTitle("Download File Info")
        self.setMinimumWidth(550)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self._setup_ui()
        self._load_remembered_directory()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(self.url)
        self.url_edit.setReadOnly(True)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)

        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["General", "Compressed", "Documents", "Music", "Pictures", "Programs", "Video", "Torrents"])
        self.cat_combo.setCurrentText(self.category)
        self.cat_combo.currentTextChanged.connect(self._on_category_changed)
        cat_layout.addWidget(self.cat_combo, stretch=1)
        
        add_cat_btn = QPushButton()
        add_cat_btn.setIcon(icons.get_icon(Icons.ADD))
        add_cat_btn.setFixedSize(24, 24)
        cat_layout.addWidget(add_cat_btn)
        
        # Add protocol options button for FTP/torrent
        if self.protocol in ["ftp", "magnet", "torrent"]:
            options_btn = QPushButton()
            options_btn.setIcon(icons.get_icon(Icons.SETTINGS))
            options_btn.setFixedSize(24, 24)
            options_btn.setToolTip(f"{self.protocol.upper()} Options")
            options_btn.clicked.connect(self._show_protocol_options)
            cat_layout.addWidget(options_btn)
        
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

        self.remember_cb = QCheckBox(f"Remember this path for this category")
        layout.addWidget(self.remember_cb)

        self.path_display = QLabel(app_settings.get_download_directory())
        self.path_display.setStyleSheet("color: #8b949e; background: #161b22; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.path_display)

        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)

        btn_layout = QHBoxLayout()
        self.later_btn = QPushButton("Download Later")
        self.start_btn = QPushButton("Start Download")
        self.start_btn.setObjectName("primaryButton")
        self.cancel_btn = QPushButton("Cancel")
        
        self.start_btn.clicked.connect(self._on_start_download)
        self.cancel_btn.clicked.connect(self.reject)
        self.later_btn.clicked.connect(lambda: self.done(2))

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
            "Pictures": Icons.FILE_IMAGE,
            "Torrents": Icons.FILE_ARCHIVE,  # Use archive icon for torrents
        }
        icon_enum = icon_map.get(cat, Icons.FILE)
        self.type_icon.setPixmap(icons.get_icon(icon_enum).pixmap(48, 48))

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder", self.path_display.text())
        if d:
            self.path_display.setText(d)
            self.selected_directory = d

    def _load_remembered_directory(self):
        """Load remembered directory for the current category, or use auto-categorized directory."""
        remembered_dir = app_settings.get_remembered_directory(self.category)
        if remembered_dir:
            self.path_display.setText(remembered_dir)
            self.selected_directory = remembered_dir
            return
        
        if app_settings.get_auto_categorize_enabled():
            category_to_file_category = {
                "Programs": "Programs",
                "Documents": "Documents",
                "Compressed": "Compressed",
                "General": "Other",
                "Video": "Video",
                "Music": "Audio",
                "Pictures": "Pictures"
            }
            file_category = category_to_file_category.get(self.category, "Other")
            
            path_manager = DownloadPathManager(app_settings.get_download_directory())
            categorized_path = str(path_manager.get_category_path(file_category))
            self.path_display.setText(categorized_path)
            self.selected_directory = categorized_path
        else:
            default_dir = app_settings.get_download_directory()
            self.path_display.setText(default_dir)
            self.selected_directory = default_dir

    def _on_category_changed(self, new_category):
        """Handle category change - load remembered directory for new category."""
        self.category = new_category
        
        remembered_dir = app_settings.get_remembered_directory(new_category)
        if remembered_dir:
            self.path_display.setText(remembered_dir)
            self.selected_directory = remembered_dir
        else:
            if app_settings.get_auto_categorize_enabled():
                category_to_file_category = {
                    "Programs": "Programs",
                    "Documents": "Documents",
                    "Compressed": "Compressed",
                    "General": "Other",
                    "Video": "Video",
                    "Music": "Audio",
                    "Pictures": "Pictures",
                    "Torrents": "Other"  # Torrents go to Other category for now
                }
                file_category = category_to_file_category.get(new_category, "Other")
                
                path_manager = DownloadPathManager(app_settings.get_download_directory())
                categorized_path = str(path_manager.get_category_path(file_category))
                self.path_display.setText(categorized_path)
                self.selected_directory = categorized_path
            else:
                default_dir = app_settings.get_download_directory()
                self.path_display.setText(default_dir)
                self.selected_directory = default_dir
        
        self._update_icon()

    def _on_start_download(self):
        """Handle start download button - save remembered directory if checkbox is checked."""
        if self.remember_cb.isChecked():
            current_category = self.cat_combo.currentText()
            current_path = self.path_display.text()
            if current_path and os.path.exists(current_path):
                app_settings.set_remembered_directory(current_category, current_path)
        self.accept()

    def get_info(self):
        return {
            "filename": self.name_edit.text(),
            "save_path": self.path_display.text(),
            "category": self.cat_combo.currentText(),
            "description": self.desc_edit.text(),
            "protocol_options": self.protocol_options
        }
    
    def _detect_protocol(self, url: str) -> str:
        """Detect the protocol from the URL."""
        if not url:
            return "http"
        url_lower = url.lower()
        if url_lower.startswith("ftp://") or url_lower.startswith("ftps://"):
            return "ftp"
        elif url_lower.startswith("magnet:"):
            return "magnet"
        elif url_lower.startswith("torrent:"):
            return "torrent"
        elif url_lower.startswith("http://"):
            return "http"
        elif url_lower.startswith("https://"):
            return "https"
        return "http"
    
    def _show_protocol_options(self):
        """Show protocol-specific options dialog."""
        try:
            from ui.dialogs.protocol_options_dialog import ProtocolOptionsDialog
            dlg = ProtocolOptionsDialog(self.protocol, self)
            if dlg.exec() == ProtocolOptionsDialog.DialogCode.Accepted:
                # Store protocol options for later use
                self.protocol_options = dlg.get_options()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to open protocol options: {str(e)}")
