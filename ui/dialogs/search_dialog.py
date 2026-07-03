"""
Spider Manager — Advanced Search Dialog
User-friendly dialog for advanced search across download history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QIcon
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
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QDateEdit,
    QCheckBox,
    QTabWidget,
    QWidget,
    QMessageBox,
    QScrollArea
)

from utils.icon_manager import icons
from resources.icons.icons import Icons
from utils.logger import get_logger
from core.history_manager import HistoryManager, HistoryEntry
from core.search_engine import SearchEngine, SearchCriteria
from utils.file_utils import format_size, format_speed

log = get_logger(__name__)


class SearchDialog(QDialog):
    """User-friendly dialog for advanced search across download history."""

    # Signal to open selected entry in history
    entry_selected = pyqtSignal(str)  # entry_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_manager = HistoryManager()
        self.search_engine = SearchEngine(self.history_manager)
        self.current_results: List[HistoryEntry] = []
        
        self.setWindowTitle("Advanced Search")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create tab widget for simple vs advanced search
        self.tab_widget = QTabWidget()
        
        # Simple search tab
        simple_tab = self._create_simple_search_tab()
        self.tab_widget.addTab(simple_tab, "Quick Search")
        
        # Advanced search tab
        advanced_tab = self._create_advanced_search_tab()
        self.tab_widget.addTab(advanced_tab, "Advanced Search")
        
        # Saved searches tab
        saved_tab = self._create_saved_searches_tab()
        self.tab_widget.addTab(saved_tab, "Saved Searches")
        
        layout.addWidget(self.tab_widget)

        # Results section
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        
        # Results count label
        self.results_count_label = QLabel("No results")
        results_layout.addWidget(self.results_count_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHorizontalHeaderLabels([
            "Filename", "Size", "Progress", "Speed", "State",
            "Category", "Date", "Tags", "Actions"
        ])
        
        # Configure table
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Filename
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Progress
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # State
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Tags
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_search_btn = QPushButton("Save Search")
        save_search_btn.clicked.connect(self._save_current_search)
        button_layout.addWidget(save_search_btn)

        button_layout.addSpacing(10)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_simple_search_tab(self) -> QWidget:
        """Create simple search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Quick search input
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.quick_search_input = QLineEdit()
        self.quick_search_input.setPlaceholderText("Enter filename, URL, or tag...")
        self.quick_search_input.setFixedHeight(32)
        self.quick_search_input.textChanged.connect(self._on_quick_search_changed)
        search_layout.addWidget(self.quick_search_input)
        
        # Search button
        search_btn = QPushButton("Search")
        search_btn.setFixedWidth(80)
        search_btn.clicked.connect(self._perform_quick_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)

        # Suggestions
        suggestions_layout = QHBoxLayout()
        suggestions_layout.addWidget(QLabel("Suggestions:"))
        self.suggestions_label = QLabel("Start typing to see suggestions...")
        suggestions_layout.addWidget(self.suggestions_label)
        suggestions_layout.addStretch()
        layout.addLayout(suggestions_layout)

        # Recent searches
        recent_layout = QHBoxLayout()
        recent_layout.addWidget(QLabel("Recent Searches:"))
        self.recent_searches_label = QLabel("No recent searches")
        recent_layout.addWidget(self.recent_searches_label)
        recent_layout.addStretch()
        layout.addLayout(recent_layout)

        layout.addStretch()
        return widget

    def _create_advanced_search_tab(self) -> QWidget:
        """Create advanced search tab."""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Basic filters
        basic_group = QGroupBox("Basic Filters")
        basic_layout = QFormLayout()
        
        # Filename
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Enter filename (supports wildcards)")
        basic_layout.addRow("Filename:", self.filename_input)
        
        # URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL (supports wildcards)")
        basic_layout.addRow("URL:", self.url_input)
        
        # Category
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItem("All Categories")
        self._populate_categories()
        basic_layout.addRow("Category:", self.category_input)
        
        # State
        self.state_combo = QComboBox()
        self.state_combo.addItems(["All States", "completed", "error", "cancelled", "paused"])
        basic_layout.addRow("State:", self.state_combo)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Tag filters
        tags_group = QGroupBox("Tag Filters")
        tags_layout = QVBoxLayout()
        
        tags_input_layout = QHBoxLayout()
        tags_input_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("tag1, tag2, tag3")
        tags_input_layout.addWidget(self.tags_input)
        tags_layout.addLayout(tags_input_layout)
        
        tags_layout.addWidget(QLabel("Note: All specified tags must match"))
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        # Date filters
        date_group = QGroupBox("Date Range")
        date_layout = QFormLayout()
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        date_layout.addRow("From:", self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        date_layout.addRow("To:", self.date_to)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        # Size filters
        size_group = QGroupBox("Size Range")
        size_layout = QFormLayout()
        
        size_min_layout = QHBoxLayout()
        size_min_layout.addWidget(QLabel("Min:"))
        self.size_min_input = QSpinBox()
        self.size_min_input.setRange(0, 1024 * 1024 * 1024)  # Up to 1TB
        self.size_min_input.setSuffix(" MB")
        self.size_min_input.setValue(0)
        size_min_layout.addWidget(self.size_min_input)
        size_layout.addRow("Minimum Size:", size_min_layout)
        
        size_max_layout = QHBoxLayout()
        size_max_layout.addWidget(QLabel("Max:"))
        self.size_max_input = QSpinBox()
        self.size_max_input.setRange(0, 1024 * 1024 * 1024)  # Up to 1TB
        self.size_max_input.setSuffix(" MB")
        self.size_max_input.setValue(1024)  # 1GB default
        size_max_layout.addWidget(self.size_max_input)
        size_layout.addRow("Maximum Size:", size_max_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # Speed filters
        speed_group = QGroupBox("Speed Range")
        speed_layout = QFormLayout()
        
        speed_min_layout = QHBoxLayout()
        speed_min_layout.addWidget(QLabel("Min:"))
        self.speed_min_input = QDoubleSpinBox()
        self.speed_min_input.setRange(0, 1000)
        self.speed_min_input.setSuffix(" MB/s")
        self.speed_min_input.setValue(0)
        speed_min_layout.addWidget(self.speed_min_input)
        speed_layout.addRow("Minimum Speed:", speed_min_layout)
        
        speed_max_layout = QHBoxLayout()
        speed_max_layout.addWidget(QLabel("Max:"))
        self.speed_max_input = QDoubleSpinBox()
        self.speed_max_input.setRange(0, 1000)
        self.speed_max_input.setSuffix(" MB/s")
        self.speed_max_input.setValue(100)
        speed_max_layout.addWidget(self.speed_max_input)
        speed_layout.addRow("Maximum Speed:", speed_max_layout)
        
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)

        # Search button
        search_btn = QPushButton("Perform Advanced Search")
        search_btn.setFixedHeight(40)
        search_btn.clicked.connect(self._perform_advanced_search)
        layout.addWidget(search_btn)

        # Reset button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.clicked.connect(self._reset_filters)
        layout.addWidget(reset_btn)

        layout.addStretch()
        return scroll

    def _create_saved_searches_tab(self) -> QWidget:
        """Create saved searches tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Saved searches list
        self.saved_searches_table = QTableWidget()
        self.saved_searches_table.setColumnCount(3)
        self.saved_searches_table.setHorizontalHeaderLabels(["Name", "Criteria", "Actions"])
        
        # Configure table
        self.saved_searches_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.saved_searches_table.setAlternatingRowColors(True)
        
        # Set column widths
        header = self.saved_searches_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Criteria
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        layout.addWidget(self.saved_searches_table)

        # Load saved searches button
        load_btn = QPushButton("Load Selected Search")
        load_btn.clicked.connect(self._load_selected_search)
        layout.addWidget(load_btn)

        # Delete saved search button
        delete_btn = QPushButton("Delete Selected Search")
        delete_btn.clicked.connect(self._delete_selected_search)
        layout.addWidget(delete_btn)

        # Refresh saved searches button
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self._refresh_saved_searches)
        layout.addWidget(refresh_btn)

        self._refresh_saved_searches()
        return widget

    def _populate_categories(self):
        """Populate category dropdown."""
        try:
            categories = self.history_manager.get_categories()
            self.category_input.clear()
            self.category_input.addItem("All Categories")
            self.category_input.addItems(categories)
        except Exception as e:
            log.error("Failed to populate categories: %s", e)

    def _on_quick_search_changed(self, text: str):
        """Handle quick search text change."""
        if len(text) >= 2:
            suggestions = self.search_engine.get_suggestions(text, limit=10)
            if suggestions:
                self.suggestions_label.setText(", ".join(suggestions[:5]))
            else:
                self.suggestions_label.setText("No suggestions")
        else:
            self.suggestions_label.setText("Start typing to see suggestions...")

    def _perform_quick_search(self):
        """Perform quick search."""
        query = self.quick_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search query")
            return
        
        try:
            self.current_results = self.search_engine.quick_search(query, limit=500)
            self._populate_results()
            self._update_results_count()
            
            # Add to recent searches
            self.search_engine.add_recent_search(query)
            self._update_recent_searches()
            
        except Exception as e:
            log.error("Failed to perform quick search: %s", e)
            QMessageBox.critical(self, "Error", f"Search failed: {e}")

    def _perform_advanced_search(self):
        """Perform advanced search."""
        try:
            # Get category
            category = ""
            if self.category_input.currentText() != "All Categories":
                category = self.category_input.currentText()
            
            # Get state
            state = ""
            if self.state_combo.currentText() != "All States":
                state = self.state_combo.currentText()
            
            # Get tags
            tags_str = self.tags_input.text().strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
            
            # Get date range
            date_from = None
            date_to = None
            if self.date_from.date().isValid():
                date_from = self.date_from.date().toPyDate()
            if self.date_to.date().isValid():
                date_to = self.date_to.date().toPyDate()
            
            # Get size range (convert MB to bytes)
            size_min = self.size_min_input.value() * 1024 * 1024 if self.size_min_input.value() > 0 else None
            size_max = self.size_max_input.value() * 1024 * 1024 if self.size_max_input.value() > 0 else None
            
            # Get speed range (convert MB/s to bytes/s)
            speed_min = self.speed_min_input.value() * 1024 * 1024 if self.speed_min_input.value() > 0 else None
            speed_max = self.speed_max_input.value() * 1024 * 1024 if self.speed_max_input.value() > 0 else None
            
            # Perform search
            self.current_results = self.search_engine.advanced_search(
                filename=self.filename_input.text().strip(),
                url=self.url_input.text().strip(),
                category=category,
                state=state,
                tags=tags,
                date_from=date_from,
                date_to=date_to,
                size_min=size_min,
                size_max=size_max,
                limit=500
            )
            
            self._populate_results()
            self._update_results_count()
            
        except Exception as e:
            log.error("Failed to perform advanced search: %s", e)
            QMessageBox.critical(self, "Error", f"Search failed: {e}")

    def _reset_filters(self):
        """Reset all advanced search filters."""
        self.filename_input.clear()
        self.url_input.clear()
        self.category_input.setCurrentIndex(0)
        self.state_combo.setCurrentIndex(0)
        self.tags_input.clear()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.size_min_input.setValue(0)
        self.size_max_input.setValue(1024)
        self.speed_min_input.setValue(0)
        self.speed_max_input.setValue(100)

    def _populate_results(self):
        """Populate results table."""
        self.results_table.setRowCount(len(self.current_results))
        
        for row, entry in enumerate(self.current_results):
            # Filename
            filename_item = QTableWidgetItem(entry.filename)
            filename_item.setData(Qt.ItemDataRole.ToolTipRole, entry.url)
            filename_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.results_table.setItem(row, 0, filename_item)
            
            # Size
            size_item = QTableWidgetItem(entry.size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 1, size_item)
            
            # Progress
            progress = entry.progress
            progress_item = QTableWidgetItem(f"{progress:.1f}%")
            progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if entry.is_completed:
                progress_item.setForeground(Qt.GlobalColor.green)
            elif entry.is_failed:
                progress_item.setForeground(Qt.GlobalColor.red)
            
            self.results_table.setItem(row, 2, progress_item)
            
            # Speed
            speed_item = QTableWidgetItem(format_speed(entry.speed))
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 3, speed_item)
            
            # State
            state_item = QTableWidgetItem(entry.state.capitalize())
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if entry.is_completed:
                state_item.setForeground(Qt.GlobalColor.green)
            elif entry.is_failed:
                state_item.setForeground(Qt.GlobalColor.red)
            elif entry.is_cancelled:
                state_item.setForeground(Qt.GlobalColor.gray)
            
            self.results_table.setItem(row, 4, state_item)
            
            # Category
            category_item = QTableWidgetItem(entry.category)
            category_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 5, category_item)
            
            # Date
            date_item = QTableWidgetItem(entry.date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 6, date_item)
            
            # Tags
            tags_str = ", ".join(entry.tags) if entry.tags else "-"
            tags_item = QTableWidgetItem(tags_str)
            self.results_table.setItem(row, 7, tags_item)
            
            # Actions button
            actions_btn = QPushButton("View")
            actions_btn.setFixedWidth(60)
            actions_btn.setProperty("entry_id", entry.id)
            actions_btn.clicked.connect(lambda _, eid=entry.id: self._view_entry(eid))
            self.results_table.setCellWidget(row, 8, actions_btn)

    def _update_results_count(self):
        """Update results count label."""
        count = len(self.current_results)
        self.results_count_label.setText(f"Found {count} result(s)")

    def _update_recent_searches(self):
        """Update recent searches label."""
        recent = self.search_engine.get_recent_searches(limit=5)
        if recent:
            self.recent_searches_label.setText(", ".join(recent))
        else:
            self.recent_searches_label.setText("No recent searches")

    def _view_entry(self, entry_id: str):
        """View entry details."""
        self.entry_selected.emit(entry_id)
        self.accept()

    def _save_current_search(self):
        """Save current search criteria."""
        name, ok = QMessageBox.getText(
            self,
            "Save Search",
            "Enter a name for this search:"
        )
        
        if ok and name.strip():
            try:
                # Determine which tab is active
                if self.tab_widget.currentIndex() == 0:  # Quick search
                    criteria = SearchCriteria(query=self.quick_search_input.text().strip())
                else:  # Advanced search
                    category = ""
                    if self.category_input.currentText() != "All Categories":
                        category = self.category_input.currentText()
                    
                    state = ""
                    if self.state_combo.currentText() != "All States":
                        state = self.state_combo.currentText()
                    
                    tags_str = self.tags_input.text().strip()
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                    
                    date_from = None
                    date_to = None
                    if self.date_from.date().isValid():
                        date_from = self.date_from.date().toPyDate()
                    if self.date_to.date().isValid():
                        date_to = self.date_to.date().toPyDate()
                    
                    size_min = self.size_min_input.value() * 1024 * 1024 if self.size_min_input.value() > 0 else None
                    size_max = self.size_max_input.value() * 1024 * 1024 if self.size_max_input.value() > 0 else None
                    
                    criteria = SearchCriteria(
                        filename=self.filename_input.text().strip(),
                        url=self.url_input.text().strip(),
                        category=category,
                        state=state,
                        tags=tags,
                        date_from=date_from,
                        date_to=date_to,
                        size_min=size_min,
                        size_max=size_max
                    )
                
                self.search_engine.save_search(name.strip(), criteria)
                self._refresh_saved_searches()
                QMessageBox.information(self, "Success", "Search saved successfully")
                
            except Exception as e:
                log.error("Failed to save search: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to save search: {e}")

    def _refresh_saved_searches(self):
        """Refresh saved searches table."""
        saved_searches = self.search_engine.get_saved_searches()
        self.saved_searches_table.setRowCount(len(saved_searches))
        
        for row, name in enumerate(saved_searches):
            criteria = self.search_engine.load_search(name)
            
            # Name
            name_item = QTableWidgetItem(name)
            self.saved_searches_table.setItem(row, 0, name_item)
            
            # Criteria summary
            criteria_summary = self._get_criteria_summary(criteria)
            criteria_item = QTableWidgetItem(criteria_summary)
            self.saved_searches_table.setItem(row, 1, criteria_item)
            
            # Actions button
            load_btn = QPushButton("Load")
            load_btn.setFixedWidth(50)
            load_btn.clicked.connect(lambda _, n=name: self._load_search_by_name(n))
            self.saved_searches_table.setCellWidget(row, 2, load_btn)

    def _get_criteria_summary(self, criteria: SearchCriteria) -> str:
        """Get a summary of search criteria."""
        parts = []
        
        if criteria.query:
            parts.append(f"Query: {criteria.query}")
        if criteria.filename:
            parts.append(f"File: {criteria.filename}")
        if criteria.url:
            parts.append(f"URL: {criteria.url}")
        if criteria.category:
            parts.append(f"Cat: {criteria.category}")
        if criteria.state:
            parts.append(f"State: {criteria.state}")
        if criteria.tags:
            parts.append(f"Tags: {', '.join(criteria.tags)}")
        
        return "; ".join(parts) if parts else "Empty criteria"

    def _load_selected_search(self):
        """Load selected saved search."""
        current_row = self.saved_searches_table.currentRow()
        if current_row >= 0:
            name_item = self.saved_searches_table.item(current_row, 0)
            if name_item:
                self._load_search_by_name(name_item.text())

    def _load_search_by_name(self, name: str):
        """Load search by name."""
        criteria = self.search_engine.load_search(name)
        if criteria:
            # Switch to appropriate tab and populate fields
            if criteria.query:
                self.tab_widget.setCurrentIndex(0)  # Quick search tab
                self.quick_search_input.setText(criteria.query)
                self._perform_quick_search()
            else:
                self.tab_widget.setCurrentIndex(1)  # Advanced search tab
                self.filename_input.setText(criteria.filename or "")
                self.url_input.setText(criteria.url or "")
                
                if criteria.category:
                    index = self.category_input.findText(criteria.category)
                    if index >= 0:
                        self.category_input.setCurrentIndex(index)
                
                if criteria.state:
                    index = self.state_combo.findText(criteria.state)
                    if index >= 0:
                        self.state_combo.setCurrentIndex(index)
                
                self.tags_input.setText(", ".join(criteria.tags) if criteria.tags else "")
                
                if criteria.date_from:
                    self.date_from.setDate(QDate.fromString(criteria.date_from.strftime("%Y-%m-%d"), Qt.DateFormat.ISODate))
                if criteria.date_to:
                    self.date_to.setDate(QDate.fromString(criteria.date_to.strftime("%Y-%m-%d"), Qt.DateFormat.ISODate))
                
                if criteria.size_min:
                    self.size_min_input.setValue(criteria.size_min // (1024 * 1024))
                if criteria.size_max:
                    self.size_max_input.setValue(criteria.size_max // (1024 * 1024))
                
                self._perform_advanced_search()

    def _delete_selected_search(self):
        """Delete selected saved search."""
        current_row = self.saved_searches_table.currentRow()
        if current_row >= 0:
            name_item = self.saved_searches_table.item(current_row, 0)
            if name_item:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Are you sure you want to delete the saved search '{name_item.text()}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    if self.search_engine.delete_saved_search(name_item.text()):
                        self._refresh_saved_searches()
                        QMessageBox.information(self, "Success", "Saved search deleted")

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.history_manager.close()
        super().closeEvent(event)
