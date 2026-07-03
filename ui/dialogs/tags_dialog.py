"""
Spider Manager — Tags Management Dialog
User-friendly dialog for creating, editing, and managing download tags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QGroupBox,
    QFormLayout,
    QColorDialog,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QScrollArea,
    QWidget,
    QFrame
)

from utils.icon_manager import icons
from resources.icons.icons import Icons
from utils.logger import get_logger
from core.tag_manager import TagManager, Tag

log = get_logger(__name__)


class TagsDialog(QDialog):
    """User-friendly dialog for managing download tags."""

    # Signal when tags are modified
    tags_modified = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tag_manager = TagManager()
        self.current_tags: List[Tag] = []
        self.selected_tag: Optional[Tag] = None
        
        self.setWindowTitle("Manage Tags")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        self._setup_ui()
        self._load_tags()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Tag list
        left_panel = self._create_tag_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - Tag editor
        right_panel = self._create_tag_editor_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Statistics section
        stats_group = QGroupBox("Tag Statistics")
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Import/Export buttons
        import_btn = QPushButton("Import Tags")
        import_btn.clicked.connect(self._import_tags)
        button_layout.addWidget(import_btn)

        export_btn = QPushButton("Export Tags")
        export_btn.clicked.connect(self._export_tags)
        button_layout.addWidget(export_btn)

        button_layout.addSpacing(10)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_tag_list_panel(self) -> QWidget:
        """Create tag list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Search input
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("Search tags...")
        self.tag_search_input.setFixedHeight(32)
        self.tag_search_input.textChanged.connect(self._on_tag_search_changed)
        search_layout.addWidget(self.tag_search_input)
        layout.addLayout(search_layout)

        # Tag table
        self.tag_table = QTableWidget()
        self.tag_table.setColumnCount(4)
        self.tag_table.setHorizontalHeaderLabels(["Name", "Color", "Usage", "Actions"])
        
        # Configure table
        self.tag_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tag_table.setAlternatingRowColors(True)
        self.tag_table.setSortingEnabled(True)
        self.tag_table.itemSelectionChanged.connect(self._on_tag_selection_changed)
        
        # Set column widths
        header = self.tag_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Color
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Usage
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        layout.addWidget(self.tag_table)

        # Quick actions
        quick_actions_layout = QHBoxLayout()
        
        new_tag_btn = QPushButton("New Tag")
        new_tag_btn.clicked.connect(self._create_new_tag)
        quick_actions_layout.addWidget(new_tag_btn)
        
        quick_actions_layout.addStretch()
        
        layout.addLayout(quick_actions_layout)

        return panel

    def _create_tag_editor_panel(self) -> QWidget:
        """Create tag editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Editor group
        editor_group = QGroupBox("Tag Editor")
        editor_layout = QFormLayout()

        # Tag name
        self.tag_name_input = QLineEdit()
        self.tag_name_input.setPlaceholderText("Enter tag name")
        self.tag_name_input.textChanged.connect(self._on_editor_changed)
        editor_layout.addRow("Name:", self.tag_name_input)

        # Color picker
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(40, 30)
        self.color_preview.setStyleSheet("background-color: #3498db; border: 1px solid #ccc;")
        color_layout.addWidget(self.color_preview)
        
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_btn)
        
        color_layout.addStretch()
        editor_layout.addRow("Color:", color_layout)

        # Description
        self.tag_description_input = QTextEdit()
        self.tag_description_input.setPlaceholderText("Enter tag description (optional)")
        self.tag_description_input.setMaximumHeight(100)
        self.tag_description_input.textChanged.connect(self._on_editor_changed)
        editor_layout.addRow("Description:", self.tag_description_input)

        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)

        # Editor buttons
        editor_buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Tag")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_tag)
        editor_buttons_layout.addWidget(self.save_btn)
        
        self.delete_btn = QPushButton("Delete Tag")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("background-color: #ff5f57; color: white;")
        self.delete_btn.clicked.connect(self._delete_tag)
        editor_buttons_layout.addWidget(self.delete_btn)
        
        editor_buttons_layout.addStretch()
        
        layout.addLayout(editor_buttons_layout)

        # Popular tags section
        popular_group = QGroupBox("Popular Tags")
        popular_layout = QVBoxLayout()
        
        self.popular_tags_label = QLabel("Loading popular tags...")
        popular_layout.addWidget(self.popular_tags_label)
        
        popular_group.setLayout(popular_layout)
        layout.addWidget(popular_group)

        layout.addStretch()

        return panel

    def _load_tags(self):
        """Load and display all tags."""
        try:
            self.current_tags = self.tag_manager.get_all_tags()
            self._populate_tag_table()
            self._update_statistics()
            self._update_popular_tags()
        except Exception as e:
            log.error("Failed to load tags: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to load tags: {e}")

    def _populate_tag_table(self):
        """Populate tag table with current tags."""
        self.tag_table.setRowCount(len(self.current_tags))
        
        for row, tag in enumerate(self.current_tags):
            # Name
            name_item = QTableWidgetItem(tag.name)
            name_item.setData(Qt.ItemDataRole.UserRole, tag.name)
            self.tag_table.setItem(row, 0, name_item)
            
            # Color preview
            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(tag.color))
            color_item.setData(Qt.ItemDataRole.ToolTipRole, tag.color)
            self.tag_table.setItem(row, 1, color_item)
            
            # Usage count
            usage_item = QTableWidgetItem(str(tag.usage_count))
            usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tag_table.setItem(row, 2, usage_item)
            
            # Actions button
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(50)
            edit_btn.setProperty("tag_name", tag.name)
            edit_btn.clicked.connect(lambda _, name=tag.name: self._select_tag_by_name(name))
            self.tag_table.setCellWidget(row, 3, edit_btn)

    def _update_statistics(self):
        """Update statistics label."""
        try:
            stats = self.tag_manager.get_statistics()
            stats_text = (
                f"Total Tags: {stats['total_tags']} | "
                f"Total Usage: {stats['total_usage']} | "
                f"Most Used: {stats['most_used_tag'] or 'N/A'} ({stats['most_used_count']})"
            )
            self.stats_label.setText(stats_text)
        except Exception as e:
            log.error("Failed to update statistics: %s", e)
            self.stats_label.setText("Statistics unavailable")

    def _update_popular_tags(self):
        """Update popular tags display."""
        try:
            popular_tags = self.tag_manager.get_popular_tags(limit=5)
            if popular_tags:
                tags_text = ", ".join([f"{tag.name} ({tag.usage_count})" for tag in popular_tags])
                self.popular_tags_label.setText(tags_text)
            else:
                self.popular_tags_label.setText("No tags yet")
        except Exception as e:
            log.error("Failed to update popular tags: %s", e)
            self.popular_tags_label.setText("Unable to load popular tags")

    def _on_tag_search_changed(self, text: str):
        """Handle tag search text change."""
        if text.strip():
            self.current_tags = self.tag_manager.search_tags(text.strip())
        else:
            self.current_tags = self.tag_manager.get_all_tags()
        self._populate_tag_table()

    def _on_tag_selection_changed(self):
        """Handle tag selection change in table."""
        selected_items = self.tag_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            tag_name = self.tag_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self._load_tag_to_editor(tag_name)
        else:
            self._clear_editor()

    def _select_tag_by_name(self, name: str):
        """Select tag by name."""
        for row in range(self.tag_table.rowCount()):
            item = self.tag_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == name:
                self.tag_table.selectRow(row)
                break

    def _load_tag_to_editor(self, name: str):
        """Load tag into editor."""
        tag = self.tag_manager.get_tag(name)
        if tag:
            self.selected_tag = tag
            self.tag_name_input.setText(tag.name)
            self.tag_name_input.setEnabled(False)  # Can't rename tags
            self._update_color_preview(tag.color)
            self.tag_description_input.setPlainText(tag.description)
            self.save_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

    def _clear_editor(self):
        """Clear editor fields."""
        self.selected_tag = None
        self.tag_name_input.clear()
        self.tag_name_input.setEnabled(True)
        self._update_color_preview("#3498db")
        self.tag_description_input.clear()
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def _create_new_tag(self):
        """Create a new tag."""
        self._clear_editor()
        self.tag_table.clearSelection()
        self.tag_name_input.setFocus()

    def _choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            self._update_color_preview(color.name())

    def _update_color_preview(self, color: str):
        """Update color preview label."""
        self.current_color = color
        self.color_preview.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")

    def _on_editor_changed(self):
        """Handle editor field changes."""
        if self.selected_tag:
            # Editing existing tag
            self.save_btn.setEnabled(True)
        else:
            # Creating new tag
            self.save_btn.setEnabled(bool(self.tag_name_input.text().strip()))

    def _save_tag(self):
        """Save tag from editor."""
        name = self.tag_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Tag name cannot be empty")
            return
        
        try:
            if self.selected_tag:
                # Update existing tag
                self.selected_tag.color = getattr(self, 'current_color', '#3498db')
                self.selected_tag.description = self.tag_description_input.toPlainText().strip()
                self.tag_manager.update_tag(self.selected_tag)
                QMessageBox.information(self, "Success", "Tag updated successfully")
            else:
                # Create new tag
                tag = Tag(
                    name=name,
                    color=getattr(self, 'current_color', '#3498db'),
                    description=self.tag_description_input.toPlainText().strip()
                )
                if self.tag_manager.create_tag(tag):
                    QMessageBox.information(self, "Success", "Tag created successfully")
                else:
                    QMessageBox.warning(self, "Warning", "Tag already exists")
            
            self._load_tags()
            self.tags_modified.emit()
            
        except Exception as e:
            log.error("Failed to save tag: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to save tag: {e}")

    def _delete_tag(self):
        """Delete selected tag."""
        if not self.selected_tag:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the tag '{self.selected_tag.name}'?\n\n"
            f"This will not remove the tag from download history entries.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.tag_manager.delete_tag(self.selected_tag.name):
                    self._load_tags()
                    self._clear_editor()
                    self.tags_modified.emit()
                    QMessageBox.information(self, "Success", "Tag deleted successfully")
                else:
                    QMessageBox.warning(self, "Not Found", "Tag not found")
            except Exception as e:
                log.error("Failed to delete tag: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to delete tag: {e}")

    def _import_tags(self):
        """Import tags from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Tags",
            str(Path.home() / "Downloads"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                reply = QMessageBox.question(
                    self,
                    "Overwrite Existing Tags?",
                    "Do you want to overwrite existing tags with the same name?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                overwrite = (reply == QMessageBox.StandardButton.Yes)
                count = self.tag_manager.import_tags(file_path, overwrite=overwrite)
                self._load_tags()
                self.tags_modified.emit()
                QMessageBox.information(self, "Success", f"Imported {count} tags")
            except Exception as e:
                log.error("Failed to import tags: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to import tags: {e}")

    def _export_tags(self):
        """Export tags to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Tags",
            str(Path.home() / "Downloads" / "tags.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.tag_manager.export_tags(file_path)
                QMessageBox.information(self, "Success", f"Tags exported to {file_path}")
            except Exception as e:
                log.error("Failed to export tags: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to export tags: {e}")

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.tag_manager.close()
        super().closeEvent(event)
