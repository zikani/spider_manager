"""
main_window.py - QMainWindow shell, layout orchestration.
"""

import asyncio
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QTimer, QUrl, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QTabBar,
    QLabel,
)
from utils.icon_manager import icons
from resources.icons.icons import Icons

from qasync import asyncSlot

from config import settings as app_settings
from core.download_engine import DownloadEngine
from core.queue_manager import QueueManager
from ui.dialogs.about import AboutDialog
from ui.dialogs.download_file_info import DownloadFileInfoDialog
from ui.dialogs.download_progress import DownloadProgressDialog
from ui.dialogs.batch_download import BatchDownloadDialog
from ui.dialogs.preferences import PreferencesDialog
from ui.dialogs.scheduler_dialog import SchedulerDialog
from ui.dialogs.speed_limiter_dialog import SpeedLimiterDialog
from ui.download_bridge import DownloadBridge
from ui.themes.theme_manager import apply_theme_to_window
from utils.clipboard_monitor import ClipboardMonitor
from ui.system_tray import SystemTrayManager
from ui.downloads_window import DownloadsWindow
from ui.widgets.category_panel import CategoryPanel
from ui.widgets.download_table import DownloadTable
from ui.widgets.speed_graph import SpeedGraph
from ui.widgets.status_bar import DownloadStatusBar
from ui.widgets.toolbar import DownloadToolbar


class SpiderMainWindow(QMainWindow):
    def __init__(
        self,
        engine: DownloadEngine,
        queue: QueueManager,
        bridge: DownloadBridge,
    ):
        super().__init__()
        self._engine = engine
        self._queue = queue
        self._bridge = bridge

        self.setWindowTitle("Spider Manager")
        self.setWindowIcon(icons.get_icon(Icons.SPIDER_LOGO))
        self.resize(1000, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._apply_theme()
        self._wire_toolbar()
        self._wire_menus()

        self._setup_tray()

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(500)

        self._bridge.tasks_changed.connect(self._on_tasks_changed)
        self._bridge.stats_changed.connect(self._refresh_stats)

        self._clipboard_monitor = ClipboardMonitor(self)
        self._clipboard_monitor.url_detected.connect(self._on_clipboard_url)
        self._sync_clipboard_monitor()

    def apply_saved_preferences(self) -> None:
        apply_theme_to_window(self)
        self._sync_clipboard_monitor()
        asyncio.ensure_future(self._queue.wake_dispatch())

    def _sync_clipboard_monitor(self) -> None:
        self._clipboard_monitor.set_enabled(app_settings.get_clipboard_monitor())

    def _setup_ui(self):
        app_container = QWidget()
        app_container.setObjectName("appContainer")
        self.setCentralWidget(app_container)

        container_layout = QVBoxLayout(app_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setObjectName("titleBar")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(14, 0, 14, 0)

        # Application icon on the left
        self.app_icon = QLabel()
        self.app_icon.setFixedSize(20, 20)
        self.app_icon.setPixmap(icons.get_icon(Icons.SPIDER_LOGO).pixmap(20, 20))
        self.app_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar_layout.addWidget(self.app_icon)
        title_bar_layout.addSpacing(8)

        # Title label in the center with dynamic context
        self.title_label = QLabel("Spider Manager")
        self.title_label.setObjectName("titleBarTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar_layout.addWidget(self.title_label, stretch=1)

        # Window state indicator
        self.state_indicator = QLabel()
        self.state_indicator.setFixedSize(16, 16)
        self.state_indicator.setStyleSheet("""
            QLabel {
                background: transparent;
                border: 1px solid #30363d;
                border-radius: 2px;
            }
        """)
        title_bar_layout.addWidget(self.state_indicator)
        title_bar_layout.addSpacing(8)

        # Window controls on the right side (Windows style)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)  # Add spacing between buttons
        
        # Minimize button
        self.minimize_btn = QWidget()
        self.minimize_btn.setFixedSize(12, 12)
        self.minimize_btn.setStyleSheet("""
            QWidget {
                background: #febc2e;
                border-radius: 6px;
            }
            QWidget:hover {
                background: #f7d39c;
            }
        """)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.mousePressEvent = self.minimize_window
        controls_layout.addWidget(self.minimize_btn)
        
        # Maximize/Restore button
        self.maximize_btn = QWidget()
        self.maximize_btn.setFixedSize(12, 12)
        self.maximize_btn.setStyleSheet("""
            QWidget {
                background: #28c840;
                border-radius: 6px;
            }
            QWidget:hover {
                background: #6dd47d;
            }
        """)
        self.maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_btn.mousePressEvent = self.toggle_maximize
        controls_layout.addWidget(self.maximize_btn)
        
        # Close button
        self.close_btn = QWidget()
        self.close_btn.setFixedSize(12, 12)
        self.close_btn.setStyleSheet("""
            QWidget {
                background: #ff5f57;
                border-radius: 6px;
            }
            QWidget:hover {
                background: #ff8b86;
            }
        """)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.mousePressEvent = self.close_window
        controls_layout.addWidget(self.close_btn)
        
        title_bar_layout.addLayout(controls_layout)
        
        container_layout.addWidget(title_bar)

        menu_bar = self.menuBar()
        menu_bar.setFixedHeight(28)
        self._menu_bar = menu_bar
        container_layout.addWidget(menu_bar)

        self.toolbar = DownloadToolbar()
        container_layout.addWidget(self.toolbar)

        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.category_panel = CategoryPanel(self._queue)
        body_layout.addWidget(self.category_panel)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.tab_bar = QTabBar()
        self.tab_bar.addTab("All Downloads")
        self.tab_bar.addTab("Queue")
        self.tab_bar.addTab("Scheduler")
        self.tab_bar.addTab("Speed Limiter")
        self.tab_bar.setCurrentIndex(0)
        content_layout.addWidget(self.tab_bar)

        self.download_table = DownloadTable(self._queue, self._bridge)
        content_layout.addWidget(self.download_table, stretch=1)

        self.speed_graph = SpeedGraph()
        content_layout.addWidget(self.speed_graph)

        body_layout.addWidget(content)
        container_layout.addWidget(body_widget)

        self.status_bar = DownloadStatusBar()
        self.setStatusBar(self.status_bar)

        self.category_panel.filter_changed.connect(self.download_table.download_model.set_filter)
        self.toolbar.search_input.textChanged.connect(self.download_table.download_model.set_search)

    def _apply_theme(self):
        apply_theme_to_window(self)

    def _wire_menus(self):
        # File Menu
        file_menu = self._menu_bar.addMenu("File")
        
        act_add_url = QAction(icons.get_icon(Icons.ADD), "Add URL...", self)
        act_add_url.setShortcut("Ctrl+N")
        act_add_url.triggered.connect(self._open_add_download)
        file_menu.addAction(act_add_url)
        
        act_batch = QAction(icons.get_icon(Icons.DOWNLOAD_ALL), "Batch Download...", self)
        act_batch.setShortcut("Ctrl+B")
        act_batch.triggered.connect(self._open_batch)
        file_menu.addAction(act_batch)
        
        file_menu.addSeparator()
        
        act_import = QAction(icons.get_icon(Icons.IMPORT), "Import from File...", self)
        act_import.setShortcut("Ctrl+I")
        act_import.triggered.connect(self._import_downloads)
        file_menu.addAction(act_import)
        
        act_export = QAction(icons.get_icon(Icons.EXPORT), "Export List...", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self._export_downloads)
        file_menu.addAction(act_export)
        
        file_menu.addSeparator()
        
        # Recent Files submenu
        recent_menu = file_menu.addMenu(icons.get_icon(Icons.HISTORY), "Recent Files")
        self._update_recent_files(recent_menu)
        
        file_menu.addSeparator()
        
        act_open_folder = QAction(icons.get_icon(Icons.FOLDER_OPEN), "Open Download Folder", self)
        act_open_folder.setShortcut("Ctrl+O")
        act_open_folder.triggered.connect(self._open_download_folder)
        file_menu.addAction(act_open_folder)
        
        file_menu.addSeparator()
        
        act_quit = QAction(icons.get_icon(Icons.STOP), "Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Edit Menu
        edit_menu = self._menu_bar.addMenu("Edit")
        
        act_select_all = QAction(icons.get_icon(Icons.SELECT_ALL), "Select All", self)
        act_select_all.setShortcut("Ctrl+A")
        act_select_all.triggered.connect(self._select_all_downloads)
        edit_menu.addAction(act_select_all)
        
        act_invert_selection = QAction(icons.get_icon(Icons.TRANSFER_ARROWS), "Invert Selection", self)
        act_invert_selection.setShortcut("Ctrl+Shift+A")
        act_invert_selection.triggered.connect(self._invert_selection)
        edit_menu.addAction(act_invert_selection)
        
        edit_menu.addSeparator()
        
        act_find = QAction(icons.get_icon(Icons.SEARCH), "Find Downloads...", self)
        act_find.setShortcut("Ctrl+F")
        act_find.triggered.connect(self._focus_search)
        edit_menu.addAction(act_find)
        
        act_clear_search = QAction(icons.get_icon(Icons.CLEAR_ALL), "Clear Search", self)
        act_clear_search.setShortcut("Esc")
        act_clear_search.triggered.connect(self._clear_search)
        edit_menu.addAction(act_clear_search)

        # View Menu
        view_menu = self._menu_bar.addMenu("View")
        
        act_prefs = QAction(icons.get_icon(Icons.SETTINGS), "Preferences...", self)
        act_prefs.setShortcut("Ctrl+,")
        act_prefs.triggered.connect(self._open_preferences)
        view_menu.addAction(act_prefs)
        
        view_menu.addSeparator()
        
        act_show_sidebar = QAction(icons.get_icon(Icons.SIDEBAR_TOGGLE), "Show Sidebar", self)
        act_show_sidebar.setCheckable(True)
        act_show_sidebar.setChecked(True)
        act_show_sidebar.setShortcut("F9")
        act_show_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(act_show_sidebar)
        
        act_show_graph = QAction(icons.get_icon(Icons.STATS), "Show Speed Graph", self)
        act_show_graph.setCheckable(True)
        act_show_graph.setChecked(True)
        act_show_graph.setShortcut("F8")
        act_show_graph.triggered.connect(self._toggle_speed_graph)
        view_menu.addAction(act_show_graph)
        
        act_show_status = QAction(icons.get_icon(Icons.INFO), "Show Status Bar", self)
        act_show_status.setCheckable(True)
        act_show_status.setChecked(True)
        act_show_status.setShortcut("F10")
        act_show_status.triggered.connect(self._toggle_status_bar)
        view_menu.addAction(act_show_status)
        
        view_menu.addSeparator()
        
        act_refresh = QAction(icons.get_icon(Icons.REFRESH), "Refresh", self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self._refresh_downloads)
        view_menu.addAction(act_refresh)
        
        act_fullscreen = QAction(icons.get_icon(Icons.FULLSCREEN), "Full Screen", self)
        act_fullscreen.setShortcut("F11")
        act_fullscreen.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(act_fullscreen)
        
        view_menu.addSeparator()
        
        act_theme = QAction(icons.get_icon(Icons.VIEW_GRID), "Switch Theme", self)
        act_theme.setShortcut("Ctrl+T")
        act_theme.triggered.connect(self._switch_theme)
        view_menu.addAction(act_theme)

        # Downloads Menu
        downloads_menu = self._menu_bar.addMenu("Downloads")
        
        act_start = QAction(icons.get_icon(Icons.PLAY), "Start Selected", self)
        act_start.setShortcut("Ctrl+S")
        act_start.triggered.connect(self._resume_selected)
        downloads_menu.addAction(act_start)
        
        act_pause = QAction(icons.get_icon(Icons.PAUSE), "Pause Selected", self)
        act_pause.setShortcut("Ctrl+P")
        act_pause.triggered.connect(self._pause_selected)
        downloads_menu.addAction(act_pause)
        
        act_cancel = QAction(icons.get_icon(Icons.STOP), "Cancel Selected", self)
        act_cancel.setShortcut("Del")
        act_cancel.triggered.connect(self._cancel_selected)
        downloads_menu.addAction(act_cancel)
        
        act_remove = QAction(icons.get_icon(Icons.DELETE), "Remove Selected", self)
        act_remove.setShortcut("Shift+Del")
        act_remove.triggered.connect(self._remove_selected)
        downloads_menu.addAction(act_remove)
        
        downloads_menu.addSeparator()
        
        act_resume_all = QAction(icons.get_icon(Icons.DOWNLOAD_ALL), "Resume All", self)
        act_resume_all.setShortcut("Ctrl+Shift+S")
        act_resume_all.triggered.connect(self._resume_all)
        downloads_menu.addAction(act_resume_all)
        
        act_pause_all = QAction(icons.get_icon(Icons.PAUSE), "Pause All", self)
        act_pause_all.setShortcut("Ctrl+Shift+P")
        act_pause_all.triggered.connect(self._pause_all)
        downloads_menu.addAction(act_pause_all)
        
        downloads_menu.addSeparator()
        
        act_restart_failed = QAction(icons.get_icon(Icons.RESTART), "Restart Failed Downloads", self)
        act_restart_failed.setShortcut("Ctrl+R")
        act_restart_failed.triggered.connect(self._restart_failed)
        downloads_menu.addAction(act_restart_failed)
        
        act_clear_completed = QAction(icons.get_icon(Icons.CLEAR_ALL), "Clear Completed", self)
        act_clear_completed.setShortcut("Ctrl+Shift+C")
        act_clear_completed.triggered.connect(self._clear_completed)
        downloads_menu.addAction(act_clear_completed)
        
        act_clear_failed = QAction(icons.get_icon(Icons.CLEAR_ALL), "Clear Failed", self)
        act_clear_failed.setShortcut("Ctrl+Shift+F")
        act_clear_failed.triggered.connect(self._clear_failed)
        downloads_menu.addAction(act_clear_failed)
        
        act_clear_all = QAction(icons.get_icon(Icons.CLEAR_ALL), "Clear All", self)
        act_clear_all.setShortcut("Ctrl+Shift+A")
        act_clear_all.triggered.connect(self._clear_all)
        downloads_menu.addAction(act_clear_all)

        # Queue Menu
        queue_menu = self._menu_bar.addMenu("Queue")
        
        act_move_top = QAction(icons.get_icon(Icons.SKIP), "Move to Top", self)
        act_move_top.setShortcut("Ctrl+Home")
        act_move_top.triggered.connect(self._move_to_top)
        queue_menu.addAction(act_move_top)
        
        act_move_up = QAction("Move Up", self)
        act_move_up.setShortcut("Ctrl+Up")
        act_move_up.triggered.connect(self._move_up)
        queue_menu.addAction(act_move_up)
        
        act_move_down = QAction("Move Down", self)
        act_move_down.setShortcut("Ctrl+Down")
        act_move_down.triggered.connect(self._move_down)
        queue_menu.addAction(act_move_down)
        
        act_move_bottom = QAction(icons.get_icon(Icons.STOP), "Move to Bottom", self)
        act_move_bottom.setShortcut("Ctrl+End")
        act_move_bottom.triggered.connect(self._move_to_bottom)
        queue_menu.addAction(act_move_bottom)
        
        queue_menu.addSeparator()
        
        act_queue_sort = QAction(icons.get_icon(Icons.SORT), "Sort Queue...", self)
        act_queue_sort.triggered.connect(self._sort_queue)
        queue_menu.addAction(act_queue_sort)
        
        act_queue_shuffle = QAction(icons.get_icon(Icons.TRANSFER_ARROWS), "Shuffle Queue", self)
        act_queue_shuffle.triggered.connect(self._shuffle_queue)
        queue_menu.addAction(act_queue_shuffle)

        # Tools Menu
        tools_menu = self._menu_bar.addMenu("Tools")
        
        act_speed_limiter = QAction(icons.get_icon(Icons.SPEED_LIMIT), "Speed Limiter...", self)
        act_speed_limiter.setShortcut("Ctrl+L")
        act_speed_limiter.triggered.connect(self._open_speed_limiter)
        tools_menu.addAction(act_speed_limiter)
        
        act_scheduler = QAction(icons.get_icon(Icons.SCHEDULER), "Scheduler...", self)
        act_scheduler.setShortcut("Ctrl+Shift+S")
        act_scheduler.triggered.connect(self._open_scheduler)
        tools_menu.addAction(act_scheduler)
        
        act_browser_integration = QAction(icons.get_icon(Icons.GLOBE), "Browser Integration...", self)
        act_browser_integration.triggered.connect(self._open_browser_integration)
        tools_menu.addAction(act_browser_integration)
        
        tools_menu.addSeparator()
        
        act_clipboard = QAction(icons.get_icon(Icons.COPY), "Clipboard Monitor", self)
        act_clipboard.setCheckable(True)
        act_clipboard.setChecked(app_settings.get_clipboard_monitor())
        act_clipboard.setShortcut("Ctrl+M")
        act_clipboard.triggered.connect(self._toggle_clipboard_monitor)
        tools_menu.addAction(act_clipboard)
        
        act_force_check = QAction(icons.get_icon(Icons.LINK), "Force Check URLs", self)
        act_force_check.triggered.connect(self._force_check_urls)
        tools_menu.addAction(act_force_check)
        
        tools_menu.addSeparator()
        
        act_cleanup = QAction(icons.get_icon(Icons.DELETE), "Cleanup...", self)
        act_cleanup.triggered.connect(self._cleanup_downloads)
        tools_menu.addAction(act_cleanup)
        
        act_stats = QAction(icons.get_icon(Icons.STATS), "Download Statistics...", self)
        act_stats.triggered.connect(self._show_statistics)
        tools_menu.addAction(act_stats)

        # Help Menu
        help_menu = self._menu_bar.addMenu("Help")
        
        act_about = QAction(icons.get_icon(Icons.INFO), "About Spider Manager", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)
        
        help_menu.addSeparator()
        
        act_docs = QAction(icons.get_icon(Icons.NOTES), "Documentation", self)
        act_docs.setShortcut("F1")
        act_docs.triggered.connect(self._open_docs)
        help_menu.addAction(act_docs)
        
        act_tutorial = QAction(icons.get_icon(Icons.PLAY), "Tutorial", self)
        act_tutorial.triggered.connect(self._open_tutorial)
        help_menu.addAction(act_tutorial)
        
        act_check_updates = QAction(icons.get_icon(Icons.REFRESH), "Check for Updates...", self)
        act_check_updates.triggered.connect(self._check_updates)
        help_menu.addAction(act_check_updates)
        
        help_menu.addSeparator()
        
        act_report = QAction(icons.get_icon(Icons.STATUS_ERROR), "Report Issue", self)
        act_report.triggered.connect(self._report_issue)
        help_menu.addAction(act_report)
        
        act_feedback = QAction(icons.get_icon(Icons.TRANSFER_ARROWS), "Send Feedback", self)
        act_feedback.triggered.connect(self._send_feedback)
        help_menu.addAction(act_feedback)
        
        help_menu.addSeparator()
        
        act_license = QAction(icons.get_icon(Icons.LOCK), "License", self)
        act_license.triggered.connect(self._show_license)
        help_menu.addAction(act_license)
        
        act_changelog = QAction(icons.get_icon(Icons.HISTORY), "Changelog", self)
        act_changelog.triggered.connect(self._show_changelog)
        help_menu.addAction(act_changelog)
        
        # Store menu actions for state management
        self._menu_actions = {
            'start_selected': act_start,
            'pause_selected': act_pause,
            'cancel_selected': act_cancel,
            'remove_selected': act_remove,
            'move_top': act_move_top,
            'move_up': act_move_up,
            'move_down': act_move_down,
            'move_bottom': act_move_bottom,
        }
        
        # Setup context menus
        self._setup_context_menus()
        
        # Update menu states
        self._update_menu_states()

    def _update_recent_files(self, recent_menu):
        """Update recent files submenu with recently downloaded files."""
        recent_menu.clear()
        
        # Get recent files from settings (mock for now)
        recent_files = []  # TODO: Implement recent files tracking
        
        if not recent_files:
            no_recent = QAction("No recent files", self)
            no_recent.setEnabled(False)
            recent_menu.addAction(no_recent)
        else:
            for file_path in recent_files[:10]:  # Show max 10 recent files
                action = QAction(file_path, self)
                action.triggered.connect(lambda checked, path=file_path: self._open_recent_file(path))
                recent_menu.addAction(action)
            
            recent_menu.addSeparator()
            clear_recent = QAction("Clear Recent Files", self)
            clear_recent.triggered.connect(self._clear_recent_files)
            recent_menu.addAction(clear_recent)

    def _setup_context_menus(self):
        """Setup context menus for different UI areas."""
        # Download table context menu
        self.download_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.download_table.customContextMenuRequested.connect(self._show_download_context_menu)
        
        # Category panel context menu
        self.category_panel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_panel.customContextMenuRequested.connect(self._show_category_context_menu)
        
        # Speed graph context menu
        self.speed_graph.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.speed_graph.customContextMenuRequested.connect(self._show_graph_context_menu)

    def _show_download_context_menu(self, position):
        """Show context menu for download table."""
        menu = QMenu(self)
        
        # Add actions based on selection
        if self.download_table.selectedIndexes():
            menu.addAction(self._menu_actions['start_selected'])
            menu.addAction(self._menu_actions['pause_selected'])
            menu.addAction(self._menu_actions['cancel_selected'])
            menu.addAction(self._menu_actions['remove_selected'])
            menu.addSeparator()
            menu.addAction(self._menu_actions['move_top'])
            menu.addAction(self._menu_actions['move_up'])
            menu.addAction(self._menu_actions['move_down'])
            menu.addAction(self._menu_actions['move_bottom'])
        else:
            act_add = QAction("Add URL...", self)
            act_add.triggered.connect(self._open_add_download)
            menu.addAction(act_add)
            
            act_batch = QAction("Batch Download...", self)
            act_batch.triggered.connect(self._open_batch)
            menu.addAction(act_batch)
        
        menu.exec(self.download_table.mapToGlobal(position))

    def _show_category_context_menu(self, position):
        """Show context menu for category panel."""
        menu = QMenu(self)
        
        act_add_category = QAction("Add Category...", self)
        act_add_category.triggered.connect(self._add_category)
        menu.addAction(act_add_category)
        
        act_edit_category = QAction("Edit Category...", self)
        act_edit_category.triggered.connect(self._edit_category)
        menu.addAction(act_edit_category)
        
        menu.exec(self.category_panel.mapToGlobal(position))

    def _show_graph_context_menu(self, position):
        """Show context menu for speed graph."""
        menu = QMenu(self)
        
        act_clear_graph = QAction("Clear Graph", self)
        act_clear_graph.triggered.connect(self._clear_speed_graph)
        menu.addAction(act_clear_graph)
        
        act_export_graph = QAction("Export Graph...", self)
        act_export_graph.triggered.connect(self._export_speed_graph)
        menu.addAction(act_export_graph)
        
        menu.exec(self.speed_graph.mapToGlobal(position))

    def _update_menu_states(self):
        """Update menu item states based on current selection and application state."""
        has_selection = bool(self.download_table.selectedIndexes())
        
        # Update download-related menu items
        if hasattr(self, '_menu_actions'):
            self._menu_actions['start_selected'].setEnabled(has_selection)
            self._menu_actions['pause_selected'].setEnabled(has_selection)
            self._menu_actions['cancel_selected'].setEnabled(has_selection)
            self._menu_actions['remove_selected'].setEnabled(has_selection)
            self._menu_actions['move_top'].setEnabled(has_selection)
            self._menu_actions['move_up'].setEnabled(has_selection)
            self._menu_actions['move_down'].setEnabled(has_selection)
            self._menu_actions['move_bottom'].setEnabled(has_selection)

    def _open_recent_file(self, file_path):
        """Open a recent file."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _clear_recent_files(self):
        """Clear recent files list."""
        # TODO: Implement recent files clearing
        pass

    def _add_category(self):
        """Add a new category."""
        # TODO: Implement add category dialog
        pass

    def _edit_category(self):
        """Edit selected category."""
        # TODO: Implement edit category dialog
        pass

    def _clear_speed_graph(self):
        """Clear the speed graph."""
        self.speed_graph.clear()

    def _export_speed_graph(self):
        """Export speed graph data."""
        # TODO: Implement graph export
        pass

    def _setup_tray(self):
        self.tray_manager = SystemTrayManager(self)
        self.tray_manager.show_window_requested.connect(self._restore_from_tray)
        self.tray_manager.quit_requested.connect(self.close)
        self.tray_manager.add_url_requested.connect(self._open_add_download)
        self.tray_manager.pause_all_requested.connect(self._pause_all)
        self.tray_manager.resume_all_requested.connect(self._resume_all)
        self.tray_manager.show_downloads_requested.connect(self._show_downloads_window)
        
        self._downloads_window = None

    def _show_downloads_window(self):
        if self._downloads_window is None or not self._downloads_window.isVisible():
            self._downloads_window = DownloadsWindow(self, self._bridge)
        self._downloads_window.show()
        self._downloads_window.raise_()
        self._downloads_window.activateWindow()

    @asyncSlot()
    async def _pause_all(self):
        await self._queue.pause_all()
        self._bridge.tasks_changed.emit()

    @asyncSlot()
    async def _resume_all(self):
        await self._queue.resume_all()
        self._bridge.tasks_changed.emit()

    def _restore_from_tray(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def _update_window_state(self):
        """Update window state indicator and title."""
        if self.isMaximized():
            self.state_indicator.setStyleSheet("""
                QLabel {
                    background: #28c840;
                    border: 1px solid #28c840;
                    border-radius: 2px;
                }
            """)
            self.title_label.setText("Spider Manager - Maximized")
        else:
            self.state_indicator.setStyleSheet("""
                QLabel {
                    background: transparent;
                    border: 1px solid #30363d;
                    border-radius: 2px;
                }
            """)
            self.title_label.setText("Spider Manager")

    def _update_title_context(self, context=""):
        """Update title bar with context information."""
        if context:
            self.title_label.setText(f"Spider Manager - {context}")
        else:
            self.title_label.setText("Spider Manager")


    def _wire_toolbar(self):
        t = self.toolbar
        t.action_add_url.triggered.connect(self._open_add_download)
        t.action_batch.triggered.connect(self._open_batch)
        t.action_resume.triggered.connect(self._resume_selected)
        t.action_pause.triggered.connect(self._pause_selected)
        t.action_cancel.triggered.connect(self._cancel_selected)
        t.action_delete.triggered.connect(self._remove_selected)
        t.action_open_folder.triggered.connect(self._open_selected_folder)
        t.action_settings.triggered.connect(self._open_preferences)

    def _selected_task_id(self) -> str | None:
        indexes = self.download_table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        task = self.download_table.download_model.task_at_row(row)
        return task.id if task else None

    def _open_add_download(self, initial_url: str = ""):
        # Instead of old AddDownloadDialog, we use the new IDM-style dialogs
        # 1. Probe the URL first
        asyncio.ensure_future(self._handle_new_download(initial_url))

    async def _handle_new_download(self, url: str):
        if not url:
            # Fallback to simple dialog if no URL
            from ui.dialogs.add_download import AddDownloadDialog
            AddDownloadDialog(self, self._engine, self._queue, self._bridge).exec()
            return

        try:
            meta = await self._engine.probe(url)
            filename = meta.get("filename", "download")
            size = int(meta.get("size", 0))
            
            # 2. Show File Info Dialog
            dlg = DownloadFileInfoDialog(self, url, filename, size)
            if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                info = dlg.get_info()
                task = self._queue.create_task(
                    url=url,
                    filename=info["filename"],
                    save_path=info["save_path"],
                    category=info["category"]
                )
                
                # Setup callbacks
                def _pc(t): self._bridge.task_progress.emit(t.id)
                def _sc(_t): self._bridge.tasks_changed.emit(); self._bridge.stats_changed.emit()
                task.progress_callback = _pc
                task.state_callback = _sc
                
                await self._queue.add(task)
                self._bridge.tasks_changed.emit()
                
                # 3. Show Progress Dialog for this specific task
                prog_dlg = DownloadProgressDialog(self, task, self._bridge)
                prog_dlg.show() # Non-blocking
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to probe URL: {str(e)}")

    def _on_clipboard_url(self, url: str):
        self._open_add_download(initial_url=url)

    def _open_batch(self):
        BatchDownloadDialog(self, self._engine, self._queue, self._bridge).exec()

    def _open_preferences(self):
        PreferencesDialog(
            self,
            self._engine,
            self._queue,
            on_saved=self.apply_saved_preferences,
        ).exec()

    @asyncSlot()
    async def _pause_selected(self):
        tid = self._selected_task_id()
        if tid:
            await self._queue.pause(tid)
            self._bridge.tasks_changed.emit()
            self._refresh_stats()

    @asyncSlot()
    async def _resume_selected(self):
        tid = self._selected_task_id()
        if tid:
            await self._queue.resume(tid)
            self._bridge.tasks_changed.emit()
            self._refresh_stats()

    @asyncSlot()
    async def _cancel_selected(self):
        tid = self._selected_task_id()
        if tid:
            await self._queue.cancel(tid)
            self._bridge.tasks_changed.emit()
            self._refresh_stats()

    def _remove_selected(self):
        tid = self._selected_task_id()
        if tid:
            self._queue.remove(tid)
            self._bridge.tasks_changed.emit()
            self._refresh_stats()

    def _open_selected_folder(self):
        indexes = self.download_table.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        task = self.download_table.download_model.task_at_row(row)
        if not task:
            return
        path = Path(task.save_path)
        if path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    @pyqtSlot()
    def _on_tasks_changed(self):
        self.category_panel.update_counts()
        self._refresh_stats()

    def _refresh_stats(self):
        asyncio.ensure_future(self._queue.wake_dispatch())
        stats = self._queue.get_stats()
        dl_path = app_settings.get_download_directory()
        self.status_bar.update_stats(stats, dl_path)
        spd = float(stats.get("total_speed") or 0)
        self.speed_graph.add_sample_mbps(spd)
        mbps = spd / (1024 * 1024)
        active_count = stats.get('active', 0)
        self.tray_manager.update_speed(mbps, active_count)
        self.category_panel.set_total_speed_mbps(mbps)
        self.title_label.setText(
            f"Spider Manager · {stats.get('active', 0)} active · {stats.get('queued', 0)} queued"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def closeEvent(self, event):
        self._queue.save_queue()
        asyncio.ensure_future(self._engine.close())
        event.accept()

    # Window control methods
    def minimize_window(self, event):
        self.showMinimized()

    def toggle_maximize(self, event):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_window_state()

    def close_window(self, event):
        self.close()

    def changeEvent(self, event):
        """Handle window state changes."""
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_window_state()
        super().changeEvent(event)

    def show_about(self):
        """Show about dialog and update title context."""
        self._update_title_context("About")
        AboutDialog(self).exec()
        self._update_title_context()


    # Menu action implementations
    def _import_downloads(self):
        # TODO: Implement import from file functionality
        pass

    def _export_downloads(self):
        # TODO: Implement export list functionality
        pass

    def _toggle_sidebar(self, checked):
        self.category_panel.setVisible(checked)

    def _toggle_speed_graph(self, checked):
        self.speed_graph.setVisible(checked)

    def _switch_theme(self):
        current = app_settings.get_ui_theme()
        new_theme = "light" if current == "dark" else "dark"
        app_settings.set_ui_theme(new_theme)
        apply_theme_to_window(self)

    def _resume_all(self):
        asyncio.ensure_future(self._queue.resume_all())

    def _pause_all(self):
        asyncio.ensure_future(self._queue.pause_all())

    def _clear_completed(self):
        self._queue.clear_by_state("completed")
        self._bridge.tasks_changed.emit()

    def _clear_failed(self):
        self._queue.clear_by_state("error")
        self._bridge.tasks_changed.emit()

    def _open_speed_limiter(self):
        SpeedLimiterDialog(self, self._engine).exec()

    def _open_scheduler(self):
        SchedulerDialog(self).exec()
        asyncio.ensure_future(self._queue.wake_dispatch())

    def _toggle_clipboard_monitor(self, checked):
        app_settings.set_clipboard_monitor(checked)
        self._sync_clipboard_monitor()

    def _open_docs(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://spider-manager.com/docs"))

    def _report_issue(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://spider-manager.com/issues"))

    def _open_download_folder(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        path = app_settings.get_download_directory()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _select_all_downloads(self):
        self.download_table.selectAll()

    def _invert_selection(self):
        self.download_table.invertSelection()

    def _focus_search(self):
        self.toolbar.search_input.setFocus()
        self.toolbar.search_input.selectAll()

    def _clear_search(self):
        self.toolbar.search_input.clear()

    def _toggle_status_bar(self, checked):
        self.status_bar.setVisible(checked)

    def _refresh_downloads(self):
        self._refresh_stats()
        self._bridge.tasks_changed.emit()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _restart_failed(self):
        asyncio.ensure_future(self._queue.restart_failed())
        self._bridge.tasks_changed.emit()

    def _clear_all(self):
        asyncio.ensure_future(self._queue.clear_all())
        self._bridge.tasks_changed.emit()

    def _move_to_top(self):
        tid = self._selected_task_id()
        if tid:
            asyncio.ensure_future(self._queue.move_to_top(tid))
            self._bridge.tasks_changed.emit()

    def _move_up(self):
        tid = self._selected_task_id()
        if tid:
            asyncio.ensure_future(self._queue.move_up(tid))
            self._bridge.tasks_changed.emit()

    def _move_down(self):
        tid = self._selected_task_id()
        if tid:
            asyncio.ensure_future(self._queue.move_down(tid))
            self._bridge.tasks_changed.emit()

    def _move_to_bottom(self):
        tid = self._selected_task_id()
        if tid:
            asyncio.ensure_future(self._queue.move_to_bottom(tid))
            self._bridge.tasks_changed.emit()

    def _sort_queue(self):
        # TODO: Implement sort dialog
        pass

    def _shuffle_queue(self):
        asyncio.ensure_future(self._queue.shuffle())
        self._bridge.tasks_changed.emit()

    def _open_browser_integration(self):
        # TODO: Implement browser integration dialog
        pass

    def _force_check_urls(self):
        asyncio.ensure_future(self._queue.force_check_all())
        self._bridge.tasks_changed.emit()

    def _cleanup_downloads(self):
        # TODO: Implement cleanup dialog
        pass

    def _show_statistics(self):
        # TODO: Implement statistics dialog
        pass

    def _open_tutorial(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://spider-manager.com/tutorial"))

    def _check_updates(self):
        # TODO: Implement update checker
        pass

    def _send_feedback(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://spider-manager.com/feedback"))

    def _show_license(self):
        # TODO: Implement license dialog
        pass

    def _show_changelog(self):
        # TODO: Implement changelog dialog
        pass
