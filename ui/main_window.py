"""
main_window.py - QMainWindow shell, layout orchestration.
"""

import asyncio
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QTimer, QUrl, pyqtSlot, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QTabBar,
    QLabel,
    QMenu,
)
from utils.icon_manager import icons
from resources.icons.icons import Icons

from qasync import asyncSlot

from config import settings as app_settings
from config.constants import DownloadState, APP_NAME, APP_VERSION
from core.download_engine import DownloadEngine
from core.queue_manager import QueueManager
from ui.dialogs.about import AboutDialog
from ui.dialogs.help_dialog import HelpDialog
from ui.dialogs.documentation_dialog import DocumentationDialog
from ui.dialogs.tutorial_dialog import TutorialDialog
from ui.dialogs.check_updates_dialog import CheckUpdatesDialog
from ui.dialogs.report_issue_dialog import ReportIssueDialog
from ui.dialogs.send_feedback_dialog import SendFeedbackDialog
from ui.dialogs.license_dialog import LicenseDialog
from ui.dialogs.changelog_dialog import ChangelogDialog
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
    # Signal for handling intercepted downloads from browser extension
    intercepted_download = pyqtSignal(dict)

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

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
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
        self._bridge.pause_resume_requested.connect(self._on_pause_resume_requested)

        self._clipboard_monitor = ClipboardMonitor(self)
        self._clipboard_monitor.url_detected.connect(self._on_clipboard_url)
        self._sync_clipboard_monitor()

        # Connect intercepted download signal to handler
        self.intercepted_download.connect(self._on_intercepted_download_slot)

        self._folder_opening = False

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

        self.app_icon = QLabel()
        self.app_icon.setFixedSize(20, 20)
        self.app_icon.setPixmap(icons.get_icon(Icons.SPIDER_LOGO).pixmap(20, 20))
        self.app_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar_layout.addWidget(self.app_icon)
        title_bar_layout.addSpacing(8)

        self.title_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.title_label.setObjectName("titleBarTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar_layout.addWidget(self.title_label, stretch=1)

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

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.minimize_btn = QLabel()
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.setPixmap(icons.get_icon(Icons.MINIMIZE).pixmap(24, 24))
        self.minimize_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minimize_btn.setStyleSheet("""
            QLabel {
                background: #febc2e;
                border-radius: 8px;
                padding: 2px;
            }
            QLabel:hover {
                background: #f7d39c;
            }
        """)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.mousePressEvent = self.minimize_window
        controls_layout.addWidget(self.minimize_btn)
        
        self.maximize_btn = QLabel()
        self.maximize_btn.setFixedSize(24, 24)
        self.maximize_btn.setPixmap(icons.get_icon(Icons.FULLSCREEN).pixmap(24, 24))
        self.maximize_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.maximize_btn.setStyleSheet("""
            QLabel {
                background: #28c840;
                border-radius: 8px;
                padding: 2px;
            }
            QLabel:hover {
                background: #6dd47d;
            }
        """)
        self.maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_btn.mousePressEvent = self.toggle_maximize
        controls_layout.addWidget(self.maximize_btn)
        
        self.close_btn = QLabel()
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setPixmap(icons.get_icon(Icons.STOP).pixmap(24, 24))
        self.close_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.close_btn.setStyleSheet("""
            QLabel {
                background: #ff5f57;
                border-radius: 8px;
                padding: 2px;
            }
            QLabel:hover {
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
        self.download_table.set_parent_window(self)
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

        help_menu = self._menu_bar.addMenu("Help")
        
        act_help = QAction(icons.get_icon(Icons.INFO), "User Guide...", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(self.show_help)
        help_menu.addAction(act_help)
        
        help_menu.addSeparator()
        
        act_about = QAction(icons.get_icon(Icons.INFO), "About Spider Manager", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)
        
        help_menu.addSeparator()
        
        act_docs = QAction(icons.get_icon(Icons.NOTES), "Documentation", self)
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
        
        self._setup_context_menus()
        
        self._update_menu_states()

    def _update_recent_files(self, recent_menu):
        """Update recent files submenu with recently downloaded files."""
        recent_menu.clear()
        
        from config import settings as app_settings
        recent_files = app_settings.get_recent_files()
        
        if not recent_files:
            no_recent = QAction("No recent files", self)
            no_recent.setEnabled(False)
            recent_menu.addAction(no_recent)
        else:
            for file_path in recent_files[:10]:
                action = QAction(file_path, self)
                action.triggered.connect(lambda checked, path=file_path: self._open_recent_file(path))
                recent_menu.addAction(action)
            
            recent_menu.addSeparator()
            clear_recent = QAction("Clear Recent Files", self)
            clear_recent.triggered.connect(self._clear_recent_files)
            recent_menu.addAction(clear_recent)

    def _setup_context_menus(self):
        """Setup context menus for different UI areas."""
        
        self.category_panel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_panel.customContextMenuRequested.connect(self._show_category_context_menu)
        
        self.speed_graph.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.speed_graph.customContextMenuRequested.connect(self._show_graph_context_menu)

    def _show_download_context_menu(self, position):
        """Show context menu for download table."""
        menu = QMenu(self)
        
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
        pass

    def _add_category(self):
        """Add a new category."""
        pass

    def _edit_category(self):
        """Edit selected category."""
        pass

    def _clear_speed_graph(self):
        """Clear the speed graph."""
        self.speed_graph.clear()

    def _export_speed_graph(self):
        """Export speed graph data."""
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
        asyncio.create_task(self._handle_new_download(initial_url))

    async def _handle_new_download(self, url: str):
        if not url:
            from ui.dialogs.add_download import AddDownloadDialog
            AddDownloadDialog(self, self._engine, self._queue, self._bridge).exec()
            return

        try:
            from plugins.yt_dlp_plugin import YtDlpPlugin
            from plugins.browser_extension import ExtensionIPCHandler
            
            is_streaming = ExtensionIPCHandler.is_streaming_url(url) or YtDlpPlugin.is_streaming_url(url)
            
            plugin = YtDlpPlugin()
            can_handle = plugin.can_handle(url)
            is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()
            
            if is_youtube or is_streaming or can_handle:
                dlg = DownloadFileInfoDialog(self, url, "video_download", 0)
                if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                    info = dlg.get_info()
                    from config.settings import get_download_directory
                    await self._handle_streaming_download_with_queue(url, info["filename"], info["save_path"], "", {})
                return
            
            meta = await self._engine.probe(url)
            filename = meta.get("filename", "download")
            size = int(meta.get("size", 0))
            
            dlg = DownloadFileInfoDialog(self, url, filename, size)
            if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                info = dlg.get_info()
                task = self._queue.create_task(
                    url=url,
                    filename=info["filename"],
                    save_path=info["save_path"],
                    category=info["category"]
                )
                
                task.total_size = size
                
                def _pc(t): self._bridge.task_progress.emit(t.id)
                def _sc(t): 
                    if t.state == DownloadState.PAUSED and t.id not in self._queue._active:
                        asyncio.create_task(self._queue.handle_natural_pause_exit(t))
                    self._bridge.tasks_changed.emit(); 
                    self._bridge.stats_changed.emit()
                task.progress_callback = _pc
                task.state_callback = _sc
                
                await self._queue.add(task)
                self._bridge.tasks_changed.emit()
                
                prog_dlg = DownloadProgressDialog(self, task, self._bridge, self._queue)
                
                prog_dlg.speed_limit_changed.connect(self._engine.set_speed_limit)
                
                prog_dlg.show()
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to probe URL: {str(e)}")

    def _on_clipboard_url(self, url: str):
        self._open_add_download(initial_url=url)

    def _on_intercepted_download(self, download_info: dict):
        """Handle download intercepted from browser extension."""
        # Emit signal instead of creating task directly to avoid async conflicts
        self.intercepted_download.emit(download_info)

    @pyqtSlot(dict)
    def _on_intercepted_download_slot(self, download_info: dict):
        """Slot for handling intercepted downloads from browser extension."""
        url = download_info.get("url")
        filename = download_info.get("filename")
        referrer = download_info.get("referrer", "")
        cookie_string = download_info.get("cookie_string")
        save_path = download_info.get("save_path")
        headers = download_info.get("headers", {})
        is_streaming = download_info.get("is_streaming", False)
        hls_info = download_info.get("hls_info")
        video_info = download_info.get("video_info")

        # Use ensure_future to schedule the async task
        asyncio.ensure_future(self._handle_intercepted_download(url, filename, save_path, referrer, headers, is_streaming, hls_info, video_info))

    async def _handle_intercepted_download(self, url: str, filename: str, save_path: str, referrer: str, headers: dict, is_streaming: bool = False, hls_info: dict = None, video_info: dict = None):
        """Handle intercepted download by showing dialog and adding to queue."""
        try:
            from plugins.yt_dlp_plugin import YtDlpPlugin
            from plugins.ftp_plugin import FTPPlugin
            from plugins.torrent_plugin import TorrentPlugin
            from plugins.plugin_base import PluginRegistry
            
            # Check URL type
            url_lower = url.lower()
            is_youtube = "youtube.com" in url_lower or "youtu.be" in url_lower
            is_ftp = url_lower.startswith("ftp://") or url_lower.startswith("ftps://")
            is_magnet = url_lower.startswith("magnet:")
            is_torrent = url_lower.endswith(".torrent")
            
            # Check if plugins can handle
            yt_plugin = YtDlpPlugin()
            ftp_plugin = FTPPlugin()
            torrent_plugin = TorrentPlugin()
            
            yt_can_handle = yt_plugin.can_handle(url)
            ftp_can_handle = ftp_plugin.can_handle(url)
            torrent_can_handle = torrent_plugin.can_handle(url)
            
            # Handle streaming/video downloads
            if is_youtube or is_streaming or hls_info or video_info or yt_can_handle:
                dlg = DownloadFileInfoDialog(self, url, filename or "video_download", 0)
                if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                    info = dlg.get_info()
                    await self._handle_streaming_download_with_queue(url, info["filename"], info["save_path"], referrer, headers, hls_info, video_info)
                return
            
            # Handle FTP downloads
            if is_ftp or ftp_can_handle:
                dlg = DownloadFileInfoDialog(self, url, filename or "ftp_download", 0)
                if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                    info = dlg.get_info()
                    await self._handle_plugin_download(url, info["filename"], info["save_path"], referrer, headers, "ftp")
                return
            
            # Handle torrent/magnet downloads
            if is_magnet or is_torrent or torrent_can_handle:
                dlg = DownloadFileInfoDialog(self, url, filename or "torrent_download", 0)
                if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                    info = dlg.get_info()
                    await self._handle_plugin_download(url, info["filename"], info["save_path"], referrer, headers, "torrent")
                return
            
            # Handle direct HTTP downloads
            await self._handle_direct_download(url, filename, save_path, referrer, headers)
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to handle intercepted download: {str(e)}")

    async def _handle_plugin_download(self, url: str, filename: str, save_path: str, referrer: str, headers: dict, protocol: str):
        """Handle plugin-based download (FTP, torrent) by adding to queue."""
        try:
            from plugins.plugin_base import PluginRegistry, PluginContext
            from core.queue_manager import DownloadState
            
            # Get the appropriate plugin
            registry = PluginRegistry.instance()
            plugin = registry.find(url)
            
            if not plugin:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", f"No plugin found for URL: {url}")
                return
            
            # Create task for plugin download
            task = self._queue.create_task(
                url=url,
                filename=filename,
                save_path=save_path,
                category="documents",  # Default category
                referrer=referrer,
                headers=headers
            )
            
            # Mark as plugin download
            task._plugin_name = plugin.name
            task._protocol = protocol
            
            def _pc(t): self._bridge.task_progress.emit(t.id)
            def _sc(t): 
                if t.state == DownloadState.PAUSED and t.id not in self._queue._active:
                    asyncio.create_task(self._queue.handle_natural_pause_exit(t))
                self._bridge.tasks_changed.emit(); 
                self._bridge.stats_changed.emit()
            task.progress_callback = _pc
            task.state_callback = _sc
            
            await self._queue.add(task)
            self._bridge.tasks_changed.emit()
            
            # Show progress dialog
            prog_dlg = DownloadProgressDialog(self, task, self._bridge, self._queue)
            prog_dlg.show()
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to handle plugin download: {str(e)}")

    async def _handle_direct_download(self, url: str, filename: str, save_path: str, referrer: str, headers: dict):
        """Handle direct HTTP download by showing dialog and adding to queue."""
        try:
            meta = await self._engine.probe(url, headers=headers)
            size = int(meta.get("size", 0))
            
            dlg = DownloadFileInfoDialog(self, url, filename, size)
            if dlg.exec() == DownloadFileInfoDialog.DialogCode.Accepted:
                info = dlg.get_info()
                task = self._queue.create_task(
                    url=url,
                    filename=info["filename"],
                    save_path=info["save_path"],
                    category=info["category"],
                    referrer=referrer,
                    headers=headers
                )
                
                task.total_size = size
                
                def _pc(t): self._bridge.task_progress.emit(t.id)
                def _sc(t): 
                    if t.state == DownloadState.PAUSED and t.id not in self._queue._active:
                        asyncio.create_task(self._queue.handle_natural_pause_exit(t))
                    self._bridge.tasks_changed.emit(); 
                    self._bridge.stats_changed.emit()
                task.progress_callback = _pc
                task.state_callback = _sc
                
                await self._queue.add(task)
                self._bridge.tasks_changed.emit()
                
                prog_dlg = DownloadProgressDialog(self, task, self._bridge, self._queue)
                prog_dlg.speed_limit_changed.connect(self._engine.set_speed_limit)
                prog_dlg.show()
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to handle direct download: {str(e)}")

    async def _handle_streaming_download_with_queue(self, url: str, filename: str, save_path: str, referrer: str, headers: dict, hls_info: dict = None, video_info: dict = None):
        """Handle streaming download using yt-dlp through the download queue."""
        try:
            task = self._queue.create_task(
                url=url,
                filename=filename,
                save_path=save_path,
                category="Video",
                referrer=referrer,
                headers=headers
            )
            
            task.download_mode = "ytdlp"
            task.total_size = 0
            
            def _pc(t): self._bridge.task_progress.emit(t.id)
            def _sc(t): 
                if t.state == DownloadState.PAUSED and t.id not in self._queue._active:
                    asyncio.create_task(self._queue.handle_natural_pause_exit(t))
                self._bridge.tasks_changed.emit(); 
                self._bridge.stats_changed.emit()
            task.progress_callback = _pc
            task.state_callback = _sc
            
            await self._queue.add(task)
            self._bridge.tasks_changed.emit()
            
            prog_dlg = DownloadProgressDialog(self, task, self._bridge, self._queue)
            prog_dlg.speed_limit_changed.connect(self._engine.set_speed_limit)
            prog_dlg.show()
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Streaming Download Error", 
                f"Failed to queue streaming download: {str(e)}")

    async def _handle_streaming_download(self, url: str, filename: str, save_path: str, referrer: str, headers: dict, hls_info: dict = None, video_info: dict = None):
        """Handle streaming download using yt-dlp (legacy method - kept for fallback)."""
        try:
            import yt_dlp
            import shutil
            from config.settings import get_download_directory
            
            ffmpeg_available = shutil.which('ffmpeg') is not None
            
            output_template = f"{save_path}/%(title)s.%(ext)s"
            
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best' if ffmpeg_available else 'best',
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'http_headers': headers,
                'merge_output_format': 'mp4' if ffmpeg_available else None,
                'ignoreerrors': True,
            }
            
            if headers.get("Cookie"):
                ydl_opts['cookiefile'] = None
            
            def run_ytdlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await asyncio.get_event_loop().run_in_executor(executor, run_ytdlp)
                
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Download Complete", "Streaming download completed successfully.")
                
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing Dependency", 
                "yt-dlp is not installed. Streaming downloads require yt-dlp.\n\nInstall it with: pip install yt-dlp")
            await self._handle_direct_download(url, filename, save_path, referrer, headers)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Streaming Download Error", 
                f"Failed to download streaming content: {str(e)}\n\nFalling back to direct download attempt.")
            await self._handle_direct_download(url, filename, save_path, referrer, headers)

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
        if self._folder_opening:
            return
            
        self._folder_opening = True
        try:
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
        finally:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self, '_folder_opening', False))

    @pyqtSlot()
    def _on_tasks_changed(self):
        self.category_panel.update_counts()
        self._refresh_stats()

    @pyqtSlot(str)
    def _on_pause_resume_requested(self, task_id: str):
        """Handle pause/resume requests from progress dialogs."""
        import asyncio
        task = self._queue._find(task_id)
        if task:
            from core.download_engine import DownloadState
            if task.state == DownloadState.PAUSED:
                asyncio.create_task(self._queue.resume(task_id))
            elif task.state in [DownloadState.DOWNLOADING, DownloadState.QUEUED]:
                asyncio.create_task(self._queue.pause(task_id))

    def _refresh_stats(self):
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
        active_downloads = len(self._queue._active)
        
        if active_downloads > 0:
            self.hide()
            event.ignore()
            return
        
        self._queue.save_queue()
        asyncio.ensure_future(self._engine.close())
        event.accept()

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

    def show_help(self):
        """Show help dialog and update title context."""
        self._update_title_context("Help")
        HelpDialog(self).exec()
        self._update_title_context()

    def _open_docs(self):
        """Show documentation dialog."""
        self._update_title_context("Documentation")
        DocumentationDialog(self).exec()
        self._update_title_context()

    def _open_tutorial(self):
        """Show tutorial dialog."""
        self._update_title_context("Tutorial")
        TutorialDialog(self).exec()
        self._update_title_context()

    def _check_updates(self):
        """Show check updates dialog."""
        self._update_title_context("Check Updates")
        CheckUpdatesDialog(self).exec()
        self._update_title_context()

    def _report_issue(self):
        """Show report issue dialog."""
        self._update_title_context("Report Issue")
        ReportIssueDialog(self).exec()
        self._update_title_context()

    def _send_feedback(self):
        """Show send feedback dialog."""
        self._update_title_context("Send Feedback")
        SendFeedbackDialog(self).exec()
        self._update_title_context()

    def _show_license(self):
        """Show license dialog."""
        self._update_title_context("License")
        LicenseDialog(self).exec()
        self._update_title_context()

    def _show_changelog(self):
        """Show changelog dialog."""
        self._update_title_context("Changelog")
        ChangelogDialog(self).exec()
        self._update_title_context()


    def _import_downloads(self):
        pass

    def _export_downloads(self):
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



    def _open_download_folder(self):
        if self._folder_opening:
            return
            
        self._folder_opening = True
        try:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            path = app_settings.get_download_directory()
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        finally:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self, '_folder_opening', False))

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
        pass

    def _shuffle_queue(self):
        asyncio.ensure_future(self._queue.shuffle())
        self._bridge.tasks_changed.emit()

    def _open_browser_integration(self):
        pass

    def _force_check_urls(self):
        asyncio.ensure_future(self._queue.force_check_all())
        self._bridge.tasks_changed.emit()

    def _cleanup_downloads(self):
        pass

    def _show_statistics(self):
        pass


    def _check_updates(self):
        pass



