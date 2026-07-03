"""
Spider Manager — Download History Dialog
User-friendly dialog for viewing and managing download history.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QMenu,
    QDateEdit,
    QCheckBox,
    QGroupBox,
    QSplitter
)

from utils.icon_manager import icons
from resources.icons.icons import Icons
from utils.logger import get_logger
from core.history_manager import HistoryManager, HistoryEntry, HistoryFilter
from utils.file_utils import format_size, format_speed

log = get_logger(__name__)


class HistoryDialog(QDialog):
    """User-friendly dialog for viewing and managing download history."""

    # Signal to reopen a download
    reopen_download = pyqtSignal(str)  # entry_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_manager = HistoryManager()
        self.current_entries: List[HistoryEntry] = []
        
        self.setWindowTitle("Download History")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        
        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Search and filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by filename or URL...")
        self.search_input.setFixedHeight(32)
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)

        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Downloads",
            "Completed",
            "Failed",
            "Cancelled",
            "Today",
            "This Week",
            "This Month"
        ])
        self.filter_combo.setFixedWidth(150)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.filter_combo)

        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self._populate_categories()
        self.category_combo.setFixedWidth(150)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_combo)

        filter_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._load_history)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # History table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Filename", "Size", "Downloaded", "Progress", "Speed",
            "State", "Category", "Date", "Duration", "Tags", "Actions"
        ])
        
        # Configure table
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Filename
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Downloaded
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Progress
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # State
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Duration
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Tags
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        layout.addWidget(self.table)

        # Statistics bar
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Export buttons
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        button_layout.addWidget(export_csv_btn)

        export_json_btn = QPushButton("Export to JSON")
        export_json_btn.clicked.connect(self._export_json)
        button_layout.addWidget(export_json_btn)

        button_layout.addSpacing(10)

        # Clear buttons
        clear_old_btn = QPushButton("Clear Old (30 days)")
        clear_old_btn.clicked.connect(self._clear_old_entries)
        button_layout.addWidget(clear_old_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet("background-color: #ff5f57; color: white;")
        clear_all_btn.clicked.connect(self._clear_all_entries)
        button_layout.addWidget(clear_all_btn)

        button_layout.addSpacing(10)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _populate_categories(self):
        """Populate category dropdown from history."""
        try:
            categories = self.history_manager.get_categories()
            self.category_combo.clear()
            self.category_combo.addItem("All Categories")
            self.category_combo.addItems(categories)
        except Exception as e:
            log.error("Failed to populate categories: %s", e)

    def _load_history(self):
        """Load and display history entries."""
        try:
            # Get filter type
            filter_map = {
                "All Downloads": HistoryFilter.ALL,
                "Completed": HistoryFilter.COMPLETED,
                "Failed": HistoryFilter.FAILED,
                "Cancelled": HistoryFilter.CANCELLED,
                "Today": HistoryFilter.TODAY,
                "This Week": HistoryFilter.THIS_WEEK,
                "This Month": HistoryFilter.THIS_MONTH
            }
            filter_type = filter_map.get(self.filter_combo.currentText(), HistoryFilter.ALL)
            
            # Get category filter
            category = ""
            if self.category_combo.currentText() != "All Categories":
                category = self.category_combo.currentText()
            
            # Get search query
            search_query = self.search_input.text().strip()
            
            # Load entries
            self.current_entries = self.history_manager.get_all_entries(
                filter_type=filter_type,
                search_query=search_query,
                category=category,
                limit=1000
            )
            
            # Populate table
            self._populate_table()
            
            # Update statistics
            self._update_stats()
            
        except Exception as e:
            log.error("Failed to load history: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to load history: {e}")

    def _populate_table(self):
        """Populate table with current entries."""
        self.table.setRowCount(len(self.current_entries))
        
        for row, entry in enumerate(self.current_entries):
            # Filename
            filename_item = QTableWidgetItem(entry.filename)
            filename_item.setData(Qt.ItemDataRole.ToolTipRole, entry.url)
            filename_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.table.setItem(row, 0, filename_item)
            
            # Size
            size_item = QTableWidgetItem(entry.size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, size_item)
            
            # Downloaded
            downloaded_item = QTableWidgetItem(format_size(entry.downloaded))
            downloaded_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, downloaded_item)
            
            # Progress
            progress = entry.progress
            progress_item = QTableWidgetItem(f"{progress:.1f}%")
            progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Color code progress
            if entry.is_completed:
                progress_item.setForeground(Qt.GlobalColor.green)
            elif entry.is_failed:
                progress_item.setForeground(Qt.GlobalColor.red)
            
            self.table.setItem(row, 3, progress_item)
            
            # Speed
            speed_item = QTableWidgetItem(format_speed(entry.speed))
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, speed_item)
            
            # State
            state_item = QTableWidgetItem(entry.state.capitalize())
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Color code state
            if entry.is_completed:
                state_item.setForeground(Qt.GlobalColor.green)
            elif entry.is_failed:
                state_item.setForeground(Qt.GlobalColor.red)
            elif entry.is_cancelled:
                state_item.setForeground(Qt.GlobalColor.gray)
            
            self.table.setItem(row, 5, state_item)
            
            # Category
            category_item = QTableWidgetItem(entry.category)
            category_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, category_item)
            
            # Date
            date_item = QTableWidgetItem(entry.date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, date_item)
            
            # Duration
            duration = entry.duration
            if duration > 0:
                duration_str = f"{duration:.1f}s"
            else:
                duration_str = "-"
            duration_item = QTableWidgetItem(duration_str)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 8, duration_item)
            
            # Tags
            tags_str = ", ".join(entry.tags) if entry.tags else "-"
            tags_item = QTableWidgetItem(tags_str)
            self.table.setItem(row, 9, tags_item)
            
            # Actions button
            actions_btn = QPushButton("⋮")
            actions_btn.setFixedWidth(30)
            actions_btn.setProperty("entry_id", entry.id)
            actions_btn.clicked.connect(lambda _, eid=entry.id: self._show_actions_menu(eid))
            self.table.setCellWidget(row, 10, actions_btn)

    def _update_stats(self):
        """Update statistics label."""
        try:
            stats = self.history_manager.get_stats()
            stats_text = (
                f"Total: {stats['total_entries']} | "
                f"Completed: {stats['completed']} | "
                f"Failed: {stats['failed']} | "
                f"Success Rate: {stats['success_rate']}% | "
                f"Downloaded: {format_size(stats['total_downloaded_bytes'])}"
            )
            self.stats_label.setText(stats_text)
        except Exception as e:
            log.error("Failed to update stats: %s", e)
            self.stats_label.setText("Statistics unavailable")

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self._load_history()

    def _on_filter_changed(self, text: str):
        """Handle filter dropdown change."""
        self._load_history()

    def _on_category_changed(self, text: str):
        """Handle category dropdown change."""
        self._load_history()

    def _show_context_menu(self, position):
        """Show context menu for table item."""
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        entry_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        entry = self.history_manager.get_entry(entry_id)
        
        if not entry:
            return
        
        menu = QMenu(self)
        
        # Copy URL
        copy_url_action = QAction("Copy URL", self)
        copy_url_action.triggered.connect(lambda: self._copy_to_clipboard(entry.url))
        menu.addAction(copy_url_action)
        
        # Copy filename
        copy_filename_action = QAction("Copy Filename", self)
        copy_filename_action.triggered.connect(lambda: self._copy_to_clipboard(entry.filename))
        menu.addAction(copy_filename_action)
        
        menu.addSeparator()
        
        # Open file location
        if entry.is_completed:
            open_location_action = QAction("Open File Location", self)
            open_location_action.triggered.connect(lambda: self._open_file_location(entry))
            menu.addAction(open_location_action)
        
        # Reopen download
        reopen_action = QAction("Reopen Download", self)
        reopen_action.triggered.connect(lambda: self._reopen_download(entry_id))
        menu.addAction(reopen_action)
        
        menu.addSeparator()
        
        # Delete entry
        delete_action = QAction("Delete Entry", self)
        delete_action.triggered.connect(lambda: self._delete_entry(entry_id))
        menu.addAction(delete_action)
        
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _show_actions_menu(self, entry_id: str):
        """Show actions menu for a specific entry."""
        entry = self.history_manager.get_entry(entry_id)
        if not entry:
            return
        
        # Get button position
        sender = self.sender()
        if not sender:
            return
        
        menu = QMenu(self)
        
        # Copy URL
        copy_url_action = QAction("Copy URL", self)
        copy_url_action.triggered.connect(lambda: self._copy_to_clipboard(entry.url))
        menu.addAction(copy_url_action)
        
        # Copy filename
        copy_filename_action = QAction("Copy Filename", self)
        copy_filename_action.triggered.connect(lambda: self._copy_to_clipboard(entry.filename))
        menu.addAction(copy_filename_action)
        
        menu.addSeparator()
        
        # Open file location
        if entry.is_completed:
            open_location_action = QAction("Open File Location", self)
            open_location_action.triggered.connect(lambda: self._open_file_location(entry))
            menu.addAction(open_location_action)
        
        # Reopen download
        reopen_action = QAction("Reopen Download", self)
        reopen_action.triggered.connect(lambda: self._reopen_download(entry_id))
        menu.addAction(reopen_action)
        
        menu.addSeparator()
        
        # Delete entry
        delete_action = QAction("Delete Entry", self)
        delete_action.triggered.connect(lambda: self._delete_entry(entry_id))
        menu.addAction(delete_action)
        
        menu.exec(sender.mapToGlobal(sender.rect().bottomLeft()))

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        log.debug("Copied to clipboard: %s", text)

    def _open_file_location(self, entry: HistoryEntry):
        """Open file location in file manager."""
        try:
            from pathlib import Path
            file_path = Path(entry.save_path) / entry.filename
            if file_path.exists():
                import subprocess
                import platform
                if platform.system() == "Windows":
                    subprocess.run(['explorer', '/select,', str(file_path)])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', '-R', str(file_path)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(file_path.parent)])
            else:
                QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
        except Exception as e:
            log.error("Failed to open file location: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to open file location: {e}")

    def _reopen_download(self, entry_id: str):
        """Reopen a download."""
        self.reopen_download.emit(entry_id)
        self.accept()

    def _delete_entry(self, entry_id: str):
        """Delete a history entry."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this history entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.history_manager.delete_entry(entry_id):
                    self._load_history()
                    QMessageBox.information(self, "Success", "Entry deleted successfully")
                else:
                    QMessageBox.warning(self, "Not Found", "Entry not found")
            except Exception as e:
                log.error("Failed to delete entry: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to delete entry: {e}")

    def _export_csv(self):
        """Export history to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History to CSV",
            str(Path.home() / "Downloads" / "download_history.csv"),
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                self.history_manager.export_to_csv(file_path)
                QMessageBox.information(self, "Success", f"History exported to {file_path}")
            except Exception as e:
                log.error("Failed to export CSV: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def _export_json(self):
        """Export history to JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History to JSON",
            str(Path.home() / "Downloads" / "download_history.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.history_manager.export_to_json(file_path)
                QMessageBox.information(self, "Success", f"History exported to {file_path}")
            except Exception as e:
                log.error("Failed to export JSON: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def _clear_old_entries(self):
        """Clear entries older than 30 days."""
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear entries older than 30 days?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = self.history_manager.clear_old_entries(30)
                self._load_history()
                QMessageBox.information(self, "Success", f"Cleared {count} old entries")
            except Exception as e:
                log.error("Failed to clear old entries: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to clear entries: {e}")

    def _clear_all_entries(self):
        """Clear all history entries."""
        reply = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Are you sure you want to clear ALL history entries? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = self.history_manager.clear_all()
                self._load_history()
                QMessageBox.information(self, "Success", f"Cleared {count} entries")
            except Exception as e:
                log.error("Failed to clear all entries: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to clear entries: {e}")

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.history_manager.close()
        super().closeEvent(event)
