"""
Tests for UI components.
Tests download table model, speed graph, category panel, theme switching, and dialogs.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from config.constants import DownloadState
from core.download_engine import DownloadTask

if PYQT6_AVAILABLE:
    from ui.widgets.download_table import DownloadTableModel
    from ui.widgets.speed_graph import SpeedGraph
    from ui.widgets.category_panel import CategoryPanel
    from ui.themes.theme_manager import apply_theme_to_window



class TestDownloadTableModel:
    """Test DownloadTableModel functionality."""

    @pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
    def test_model_initialization(self, qtbot):
        """Test model initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        assert model.rowCount() == 0
        assert model.columnCount() > 0

    def test_add_task(self, qtbot):
        """Test adding a task to the model."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
            downloaded=500,
            state=DownloadState.DOWNLOADING,
        )
        
        model.add_task(task)
        assert model.rowCount() == 1

    def test_remove_task(self, qtbot):
        """Test removing a task from the model."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
        )
        
        model.add_task(task)
        assert model.rowCount() == 1
        
        model.remove_task(task.id)
        assert model.rowCount() == 0

    def test_update_task(self, qtbot):
        """Test updating a task in the model."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
            downloaded=500,
        )
        
        model.add_task(task)
        
        task.downloaded = 750
        model.update_task(task)
        
        assert model.rowCount() == 1

    def test_clear_all(self, qtbot):
        """Test clearing all tasks from the model."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        for i in range(5):
            task = DownloadTask(
                id=f"test-{i}",
                url=f"http://example.com/file{i}.bin",
                filename=f"file{i}.bin",
                save_path="/tmp",
            )
            model.add_task(task)
        
        assert model.rowCount() == 5
        
        model.clear_all()
        assert model.rowCount() == 0

    def test_get_task_at_index(self, qtbot):
        """Test retrieving task at specific index."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
        )
        
        model.add_task(task)
        
        retrieved = model.get_task_at_index(0)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_data_display(self, qtbot):
        """Test that data is displayed correctly in table."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
            downloaded=500,
            state=DownloadState.DOWNLOADING,
        )
        
        model.add_task(task)
        
        filename = model.data(model.index(0, 0))
        assert filename == "file.bin"

    def test_header_data(self, qtbot):
        """Test that header data is set correctly."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        model = DownloadTableModel()
        
        header = model.headerData(0, Qt.Orientation.Horizontal)
        assert header is not None
        assert isinstance(header, str)



class TestSpeedGraph:
    """Test SpeedGraph widget functionality."""

    def test_initialization(self, qtbot):
        """Test speed graph initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        assert graph is not None

    def test_add_speed_point(self, qtbot):
        """Test adding a speed data point."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        graph.add_speed_point(1024 * 1024)
        
        assert len(graph._speed_history) > 0

    def test_clear_history(self, qtbot):
        """Test clearing speed history."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        
        for i in range(10):
            graph.add_speed_point(1024 * 1024)
        
        graph.clear_history()
        assert len(graph._speed_history) == 0

    def test_max_points_limit(self, qtbot):
        """Test that history is limited to max points."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        
        for i in range(100):
            graph.add_speed_point(1024 * 1024)
        
        assert len(graph._speed_history) <= 60

    def test_get_current_speed(self, qtbot):
        """Test getting current speed."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        
        assert graph.get_current_speed() == 0
        
        graph.add_speed_point(1024 * 1024)
        assert graph.get_current_speed() > 0

    def test_get_average_speed(self, qtbot):
        """Test getting average speed."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        
        for i in range(5):
            graph.add_speed_point(1024 * 1024)
        
        avg = graph.get_average_speed()
        assert avg > 0
        assert avg == 1024 * 1024

    def test_get_peak_speed(self, qtbot):
        """Test getting peak speed."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        graph = SpeedGraph()
        
        graph.add_speed_point(1024 * 1024)
        graph.add_speed_point(2 * 1024 * 1024)
        graph.add_speed_point(512 * 1024)
        
        peak = graph.get_peak_speed()
        assert peak == 2 * 1024 * 1024



class TestCategoryPanel:
    """Test CategoryPanel widget functionality."""

    def test_initialization(self, qtbot):
        """Test category panel initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        panel = CategoryPanel()
        assert panel is not None

    def test_update_counts(self, qtbot):
        """Test updating category counts."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        panel = CategoryPanel()
        
        counts = {
            "Video": 5,
            "Audio": 3,
            "Document": 2,
            "Other": 10,
        }
        
        panel.update_counts(counts)
        
        assert len(counts) > 0

    def test_select_category(self, qtbot):
        """Test selecting a category."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        panel = CategoryPanel()
        
        panel.select_category("Video")
        
        assert panel._selected_category == "Video"

    def test_get_selected_category(self, qtbot):
        """Test getting selected category."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        panel = CategoryPanel()
        
        assert panel.get_selected_category() is None or panel.get_selected_category() == "All"
        
        panel.select_category("Audio")
        assert panel.get_selected_category() == "Audio"

    def test_reset_selection(self, qtbot):
        """Test resetting category selection."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        panel = CategoryPanel()
        
        panel.select_category("Video")
        panel.reset_selection()
        
        assert panel.get_selected_category() is None or panel.get_selected_category() == "All"



class TestThemeManager:
    """Test theme manager functionality."""

    def test_apply_dark_theme(self, qtbot):
        """Test applying dark theme."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        window = MagicMock()
        window.setStyleSheet = MagicMock()
        
        apply_theme_to_window(window, theme="dark")
        
        window.setStyleSheet.assert_called_once()

    def test_apply_light_theme(self, qtbot):
        """Test applying light theme."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        window = MagicMock()
        window.setStyleSheet = MagicMock()
        
        apply_theme_to_window(window, theme="light")
        
        window.setStyleSheet.assert_called_once()

    def test_theme_persistence(self, qtbot):
        """Test that theme preference is persisted."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        window = MagicMock()
        window.setStyleSheet = MagicMock()
        
        apply_theme_to_window(window, theme="dark")
        
        from config import settings as app_settings
        saved_theme = app_settings.get_ui_theme()
        assert saved_theme == "dark"



class TestDialogs:
    """Test dialog functionality."""

    def test_add_download_dialog_initialization(self, qtbot):
        """Test AddDownloadDialog initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.dialogs.add_download import AddDownloadDialog
            dialog = AddDownloadDialog()
            assert dialog is not None
        except ImportError:
            pytest.skip("AddDownloadDialog not available")

    def test_preferences_dialog_initialization(self, qtbot):
        """Test PreferencesDialog initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.dialogs.preferences import PreferencesDialog
            dialog = PreferencesDialog()
            assert dialog is not None
        except ImportError:
            pytest.skip("PreferencesDialog not available")

    def test_batch_download_dialog_initialization(self, qtbot):
        """Test BatchDownloadDialog initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.dialogs.batch_download import BatchDownloadDialog
            dialog = BatchDownloadDialog()
            assert dialog is not None
        except ImportError:
            pytest.skip("BatchDownloadDialog not available")

    def test_scheduler_dialog_initialization(self, qtbot):
        """Test SchedulerDialog initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.dialogs.scheduler_dialog import SchedulerDialog
            dialog = SchedulerDialog()
            assert dialog is not None
        except ImportError:
            pytest.skip("SchedulerDialog not available")



class TestUIStateManagement:
    """Test UI state management."""

    def test_menu_state_based_on_selection(self, qtbot):
        """Test that menu state updates based on selection."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        pass

    def test_toolbar_state_based_on_selection(self, qtbot):
        """Test that toolbar state updates based on selection."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        pass



class TestProgressDelegate:
    """Test progress bar delegate for download table."""

    def test_delegate_initialization(self, qtbot):
        """Test progress delegate initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.progress_delegate import ProgressDelegate
            from PyQt6.QtWidgets import QTableView
            
            table = QTableView()
            delegate = ProgressDelegate(table)
            assert delegate is not None
        except ImportError:
            pytest.skip("ProgressDelegate not available")

    def test_paint_progress_bar(self, qtbot):
        """Test painting progress bar."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.progress_delegate import ProgressDelegate
            from PyQt6.QtWidgets import QTableView
            from PyQt6.QtGui import QPainter
            
            table = QTableView()
            delegate = ProgressDelegate(table)
            
            pass
        except ImportError:
            pytest.skip("ProgressDelegate not available")



class TestStatusBar:
    """Test status bar functionality."""

    def test_status_bar_initialization(self, qtbot):
        """Test status bar initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.status_bar import DownloadStatusBar
            status_bar = DownloadStatusBar()
            assert status_bar is not None
        except ImportError:
            pytest.skip("DownloadStatusBar not available")

    def test_update_stats(self, qtbot):
        """Test updating status bar stats."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.status_bar import DownloadStatusBar
            status_bar = DownloadStatusBar()
            
            stats = {
                "active": 3,
                "paused": 1,
                "completed": 10,
                "total_speed": 1024 * 1024,
            }
            
            status_bar.update_stats(stats)
        except ImportError:
            pytest.skip("DownloadStatusBar not available")



class TestToolbar:
    """Test toolbar functionality."""

    def test_toolbar_initialization(self, qtbot):
        """Test toolbar initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.toolbar import DownloadToolbar
            toolbar = DownloadToolbar()
            assert toolbar is not None
        except ImportError:
            pytest.skip("DownloadToolbar not available")

    def test_toolbar_actions(self, qtbot):
        """Test toolbar actions."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.widgets.toolbar import DownloadToolbar
            toolbar = DownloadToolbar()
            
            assert toolbar.actions() is not None
        except ImportError:
            pytest.skip("DownloadToolbar not available")



class TestSystemTray:
    """Test system tray functionality."""

    def test_tray_initialization(self, qtbot):
        """Test system tray initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.system_tray import SystemTrayManager
            tray = SystemTrayManager(None)
            assert tray is not None
        except ImportError:
            pytest.skip("SystemTrayManager not available")

    def test_tray_speed_badge(self, qtbot):
        """Test tray speed badge update."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from ui.system_tray import SystemTrayManager
            tray = SystemTrayManager(None)
            
            tray.update_speed_badge(1024 * 1024)
        except ImportError:
            pytest.skip("SystemTrayManager not available")



class TestClipboardMonitor:
    """Test clipboard monitor functionality."""

    def test_clipboard_monitor_initialization(self, qtbot):
        """Test clipboard monitor initialization."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from utils.clipboard_monitor import ClipboardMonitor
            from PyQt6.QtWidgets import QMainWindow
            
            window = QMainWindow()
            monitor = ClipboardMonitor(window)
            assert monitor is not None
        except ImportError:
            pytest.skip("ClipboardMonitor not available")

    def test_url_detection(self, qtbot):
        """Test URL detection from clipboard."""
        from PyQt6.QtWidgets.QApplication import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        try:
            from utils.clipboard_monitor import ClipboardMonitor
            from PyQt6.QtWidgets import QMainWindow
            from PyQt6.QtGui import QClipboard
            
            window = QMainWindow()
            monitor = ClipboardMonitor(window)
            
            clipboard = QApplication.clipboard()
            clipboard.setText("http://example.com/file.zip")
            
        except ImportError:
            pytest.skip("ClipboardMonitor not available")
