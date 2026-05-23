"""
download_table.py - QTableView with custom model backed by QueueManager.
"""

from __future__ import annotations

import humanize
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSlot, QSize, QPoint
from PyQt6.QtGui import QColor, QIcon, QAction
from PyQt6.QtWidgets import QTableView, QHeaderView, QMenu
from utils.icon_manager import icons
from resources.icons.icons import Icons

from config.constants import DownloadState
from core.download_engine import DownloadTask
from core.queue_manager import QueueManager
from ui.download_bridge import DownloadBridge

from .progress_delegate import ProgressDelegate

STATE_SVG = {
    "dl": Icons.PLAY,
    "ok": Icons.STATUS_COMPLETE,
    "ps": Icons.PAUSE,
    "er": Icons.STATUS_ERROR,
    "q": Icons.STATUS_QUEUED,
    "ca": Icons.STOP,
}
STATE_COLORS = {
    "dl": "#58a6ff",
    "ok": "#3fb950",
    "ps": "#d29922",
    "er": "#f78166",
    "q": "#8b949e",
    "ca": "#8b949e",
}
STATE_BG_COLORS = {
    "dl": "rgba(88,166,255,0.15)",
    "ok": "rgba(63,185,80,0.15)",
    "ps": "rgba(210,153,34,0.15)",
    "er": "rgba(247,129,102,0.15)",
    "q": "rgba(139,148,158,0.15)",
    "ca": "rgba(139,148,158,0.15)",
}
CAT_COLORS = {
    "Video": "#58a6ff",
    "Audio": "#3fb950",
    "Document": "#d29922",
    "Image": "#a371f7",
    "Archive": "#f78166",
    "Program": "#8b949e",
    "Other": "#8b949e",
}
CAT_BG_COLORS = {
    "Video": "rgba(88,166,255,0.12)",
    "Audio": "rgba(63,185,80,0.12)",
    "Document": "rgba(210,153,34,0.12)",
    "Image": "rgba(163,113,247,0.12)",
    "Archive": "rgba(247,129,102,0.12)",
    "Program": "rgba(139,148,158,0.12)",
    "Other": "rgba(139,148,158,0.12)",
}


def _ui_state(task: DownloadTask) -> str:
    s = task.state
    if s == DownloadState.DOWNLOADING or s == DownloadState.MERGING:
        return "dl"
    if s == DownloadState.COMPLETED:
        return "ok"
    if s == DownloadState.PAUSED:
        return "ps"
    if s == DownloadState.ERROR:
        return "er"
    if s == DownloadState.CANCELLED:
        return "ca"
    return "q"


def _fmt_eta(seconds: int) -> str:
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _fmt_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:.0f}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m}m"
    d, h = divmod(h, 24)
    return f"{d}d {h}h"


class DownloadModel(QAbstractTableModel):
    HEADERS = ["", "Filename", "Size", "Progress", "Speed", "ETA", "Time", "Category", "Actions"]

    def __init__(
        self,
        queue: QueueManager,
        bridge: DownloadBridge,
        parent=None,
    ):
        super().__init__(parent)
        self._queue = queue
        self._bridge = bridge
        self._filter = "all"
        self._search = ""
        bridge.tasks_changed.connect(self._on_tasks_changed)
        bridge.stats_changed.connect(self._on_tasks_changed)
        bridge.task_progress.connect(self._on_task_progress)

    def set_filter(self, key: str) -> None:
        self._filter = key
        self.beginResetModel()
        self.endResetModel()

    def set_search(self, text: str) -> None:
        self._search = (text or "").strip().lower()
        self.beginResetModel()
        self.endResetModel()

    def _visible_tasks(self) -> list[DownloadTask]:
        tasks = self._queue.tasks_snapshot()
        out: list[DownloadTask] = []
        for t in tasks:
            if self._filter == "all":
                pass
            elif self._filter == "downloading":
                if t.state != DownloadState.DOWNLOADING and t.state != DownloadState.MERGING:
                    continue
            elif self._filter == "paused":
                if t.state != DownloadState.PAUSED:
                    continue
            elif self._filter == "completed":
                if t.state != DownloadState.COMPLETED:
                    continue
            elif self._filter == "failed":
                if t.state != DownloadState.ERROR and t.state != DownloadState.CANCELLED:
                    continue
            elif self._filter.startswith("cat:"):
                want = self._filter[4:]
                if t.category != want:
                    continue
            if self._search and self._search not in t.filename.lower():
                continue
            out.append(t)
        return out

    def task_at_row(self, row: int) -> DownloadTask | None:
        vis = self._visible_tasks()
        if 0 <= row < len(vis):
            return vis[row]
        return None

    @pyqtSlot()
    def _on_tasks_changed(self):
        self.beginResetModel()
        self.endResetModel()

    @pyqtSlot(str)
    def _on_task_progress(self, task_id: str):
        vis = self._visible_tasks()
        for row, t in enumerate(vis):
            if t.id == task_id:
                tl = self.index(row, 0)
                br = self.index(row, len(self.HEADERS) - 1)
                self.dataChanged.emit(
                    tl,
                    br,
                    [
                        Qt.ItemDataRole.DisplayRole,
                        Qt.ItemDataRole.UserRole,
                        Qt.ItemDataRole.ForegroundRole,
                        Qt.ItemDataRole.BackgroundRole,
                    ],
                )
                return

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._visible_tasks())

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        tasks = self._visible_tasks()
        row = index.row()
        if row >= len(tasks):
            return None
        task = tasks[row]
        col = index.column()
        st = _ui_state(task)

        if role == Qt.ItemDataRole.DecorationRole:
            if col == 0:
                return icons.get_icon(STATE_SVG.get(st, Icons.STATUS_QUEUED))
            if col == 7:
                cat_icons = {
                    "Video": Icons.FILE_VIDEO,
                    "Audio": Icons.FILE_AUDIO,
                    "Document": Icons.FILE,
                    "Archive": Icons.FILE_ARCHIVE,
                    "Program": Icons.SETTINGS,
                }
                return icons.get_icon(cat_icons.get(task.category, Icons.FILE))
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return None
            if col == 1:
                return task.filename
            if col == 2:
                if task.total_size > 0:
                    return humanize.naturalsize(task.total_size, binary=True)
                return "—"
            if col == 3:
                if task.total_size > 0:
                    return f"{round(task.progress, 1)}% ({humanize.naturalsize(task.downloaded, binary=True)})"
                return f"{round(task.progress, 1)}%"
            if col == 4:
                if st != "dl" or task.speed <= 0:
                    return "—"
                return humanize.naturalsize(task.speed, binary=True) + "/s"
            if col == 5:
                if st == "ok":
                    return "done"
                if st == "er":
                    return task.error[:24] + "…" if len(task.error) > 24 else task.error
                if st == "ca":
                    return "cancelled"
                return _fmt_eta(task.eta)
            if col == 6:
                import time
                if st == "ok" and task.completed_at and task.started_at:
                    duration = task.completed_at - task.started_at
                    return _fmt_duration(duration)
                elif task.started_at:
                    elapsed = time.time() - task.started_at
                    return _fmt_duration(elapsed)
                return "—"
            if col == 7:
                return task.category
            if col == 8:
                return self._action_text(st)
        if role == Qt.ItemDataRole.UserRole:
            if col == 3:
                return task.progress
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return QColor(STATE_COLORS.get(st, "#8b949e"))
            if col == 4 and st == "dl":
                return QColor("#58a6ff")
            if col == 7:
                return QColor(CAT_COLORS.get(task.category, "#8b949e"))
        if role == Qt.ItemDataRole.BackgroundRole:
            if col == 0:
                return QColor(STATE_BG_COLORS.get(st, "transparent"))
            if col == 7:
                return QColor(CAT_BG_COLORS.get(task.category, "transparent"))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def _action_text(self, state: str) -> str:
        return "⚙"

    def get_overall_statistics(self) -> dict:
        """Get comprehensive statistics for all downloads."""
        tasks = self._queue.tasks_snapshot()
        
        total_downloads = len(tasks)
        completed = len([t for t in tasks if t.state == DownloadState.COMPLETED])
        failed = len([t for t in tasks if t.state in [DownloadState.ERROR, DownloadState.CANCELLED]])
        downloading = len([t for t in tasks if t.state == DownloadState.DOWNLOADING])
        paused = len([t for t in tasks if t.state == DownloadState.PAUSED])
        queued = len([t for t in tasks if t.state == DownloadState.QUEUED])
        
        total_size = sum(t.total_size for t in tasks)
        total_downloaded = sum(t.downloaded for t in tasks)
        current_speed = sum(t.speed for t in tasks if t.state == DownloadState.DOWNLOADING)
        
        overall_progress = (total_downloaded / total_size * 100) if total_size > 0 else 0
        
        import time
        current_time = time.time()
        total_download_time = 0
        active_downloads = []
        
        for task in tasks:
            if task.completed_at and task.started_at:
                total_download_time += (task.completed_at - task.started_at)
            elif task.started_at and task.state == DownloadState.DOWNLOADING:
                active_downloads.append(task)
                total_download_time += (current_time - task.started_at)
        
        avg_speed = 0
        if total_download_time > 0:
            avg_speed = total_downloaded / total_download_time
        
        category_stats = {}
        for task in tasks:
            cat = task.category
            if cat not in category_stats:
                category_stats[cat] = {
                    'count': 0,
                    'size': 0,
                    'downloaded': 0,
                    'completed': 0
                }
            category_stats[cat]['count'] += 1
            category_stats[cat]['size'] += task.total_size
            category_stats[cat]['downloaded'] += task.downloaded
            if task.state == DownloadState.COMPLETED:
                category_stats[cat]['completed'] += 1
        
        return {
            'total_downloads': total_downloads,
            'completed': completed,
            'failed': failed,
            'downloading': downloading,
            'paused': paused,
            'queued': queued,
            'total_size': total_size,
            'total_downloaded': total_downloaded,
            'current_speed': current_speed,
            'overall_progress': overall_progress,
            'average_speed': avg_speed,
            'total_download_time': total_download_time,
            'active_downloads': len(active_downloads),
            'category_stats': category_stats
        }
    
    def get_filtered_statistics(self) -> dict:
        """Get statistics for currently filtered view."""
        tasks = self._visible_tasks()
        
        total_downloads = len(tasks)
        completed = len([t for t in tasks if t.state == DownloadState.COMPLETED])
        failed = len([t for t in tasks if t.state in [DownloadState.ERROR, DownloadState.CANCELLED]])
        downloading = len([t for t in tasks if t.state == DownloadState.DOWNLOADING])
        paused = len([t for t in tasks if t.state == DownloadState.PAUSED])
        queued = len([t for t in tasks if t.state == DownloadState.QUEUED])
        
        total_size = sum(t.total_size for t in tasks)
        total_downloaded = sum(t.downloaded for t in tasks)
        current_speed = sum(t.speed for t in tasks if t.state == DownloadState.DOWNLOADING)
        overall_progress = (total_downloaded / total_size * 100) if total_size > 0 else 0
        
        return {
            'total_downloads': total_downloads,
            'completed': completed,
            'failed': failed,
            'downloading': downloading,
            'paused': paused,
            'queued': queued,
            'total_size': total_size,
            'total_downloaded': total_downloaded,
            'current_speed': current_speed,
            'overall_progress': overall_progress
        }

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None


class DownloadTable(QTableView):
    def __init__(self, queue: QueueManager, bridge: DownloadBridge):
        super().__init__()
        self._model = DownloadModel(queue, bridge, self)
        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 28)
        self.setColumnWidth(2, 80)
        self.setColumnWidth(3, 150)
        self.setColumnWidth(4, 90)
        self.setColumnWidth(5, 80)
        self.setColumnWidth(6, 80)
        self.progress_delegate = ProgressDelegate()
        self.setItemDelegateForColumn(3, self.progress_delegate)
        
        self.doubleClicked.connect(self._on_double_click)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._queue = queue
        self._bridge = bridge
        self._parent_window = None
        
        self._folder_opening = False
        self._file_opening = False
    
    def set_parent_window(self, parent_window):
        """Set the parent window reference for dialog creation."""
        self._parent_window = parent_window
    
    def _on_double_click(self, index):
        """Handle double-click on a download row to show progress dialog."""
        if not self._parent_window:
            return
            
        task = self._model.task_at_row(index.row())
        if task:
            from ui.dialogs.download_progress import DownloadProgressDialog
            prog_dlg = DownloadProgressDialog(self._parent_window, task, self._bridge, self._queue)
            prog_dlg.show()
    
    def _show_context_menu(self, pos):
        """Show IDM-style right-click context menu for download actions."""
        if not self._parent_window:
            return
            
        index = self.indexAt(pos)
        if not index.isValid():
            return
            
        task = self._model.task_at_row(index.row())
        if not task:
            return
            
        menu = QMenu(self)
        
        if task.state in [DownloadState.PAUSED, DownloadState.QUEUED]:
            resume_pause_action = QAction("Resume" if task.state == DownloadState.PAUSED else "Start Download", self)
            resume_pause_action.setIcon(icons.get_icon(Icons.PLAY))
            resume_pause_action.setShortcut("Ctrl+S")
            resume_pause_action.triggered.connect(lambda checked, t=task: self._toggle_task_pause(t))
            menu.addAction(resume_pause_action)
        elif task.state == DownloadState.DOWNLOADING:
            pause_action = QAction("Pause", self)
            pause_action.setIcon(icons.get_icon(Icons.PAUSE))
            pause_action.setShortcut("Ctrl+P")
            pause_action.triggered.connect(lambda checked, t=task: self._toggle_task_pause(t))
            menu.addAction(pause_action)
            
            stop_action = QAction("Stop", self)
            stop_action.setIcon(icons.get_icon(Icons.STOP))
            stop_action.setShortcut("Ctrl+Alt+S")
            stop_action.triggered.connect(lambda checked, t=task: self._stop_task(t))
            menu.addAction(stop_action)
        
        menu.addSeparator()
        show_progress_action = QAction("Show Progress Dialog", self)
        show_progress_action.setIcon(icons.get_icon(Icons.STATUS_COMPLETE))
        show_progress_action.setShortcut("Ctrl+D")
        show_progress_action.triggered.connect(lambda checked, t=task: self._show_progress_dialog(t))
        menu.addAction(show_progress_action)
        
        menu.addSeparator()
        
        properties_action = QAction("Properties", self)
        properties_action.setIcon(icons.get_icon(Icons.SETTINGS))
        properties_action.setShortcut("Alt+Enter")
        properties_action.triggered.connect(lambda checked, t=task: self._show_properties_window(t))
        menu.addAction(properties_action)
        
        if task.state == DownloadState.COMPLETED:
            open_file_action = QAction("Open Downloaded File", self)
            open_file_action.setIcon(icons.get_icon(Icons.FILE))
            open_file_action.setShortcut("Ctrl+O")
            open_file_action.triggered.connect(lambda checked, t=task: self._open_file(t))
            menu.addAction(open_file_action)
            
            open_folder_action = QAction("Open Download Folder", self)
            open_folder_action.setIcon(icons.get_icon(Icons.FOLDER))
            open_folder_action.setShortcut("Ctrl+F")
            open_folder_action.triggered.connect(lambda checked, t=task: self._open_folder(t))
            menu.addAction(open_folder_action)
        
        menu.addSeparator()
        copy_url_action = QAction("Copy Download Link", self)
        copy_url_action.setIcon(icons.get_icon(Icons.LINK))
        copy_url_action.setShortcut("Ctrl+C")
        copy_url_action.triggered.connect(lambda checked, t=task: self._copy_url(t))
        menu.addAction(copy_url_action)
        
        copy_all_action = QAction("Copy URL to Clipboard", self)
        copy_all_action.setIcon(icons.get_icon(Icons.LINK))
        copy_all_action.triggered.connect(lambda checked, t=task: self._copy_url(t))
        menu.addAction(copy_all_action)
        
        copy_filename_url_action = QAction("Copy URL with Filename", self)
        copy_filename_url_action.setIcon(icons.get_icon(Icons.LINK))
        copy_filename_url_action.triggered.connect(lambda checked, t=task: self._copy_url_with_filename(t))
        menu.addAction(copy_filename_url_action)
        
        open_browser_action = QAction("Open URL in Browser", self)
        open_browser_action.setIcon(icons.get_icon(Icons.GLOBE))
        open_browser_action.triggered.connect(lambda checked, t=task: self._open_in_browser(t))
        menu.addAction(open_browser_action)
        
        menu.addSeparator()
        
        if task.state in [DownloadState.QUEUED, DownloadState.PAUSED]:
            move_top_action = QAction("Move to Top", self)
            move_top_action.setIcon(icons.get_icon(Icons.PLAY))
            move_top_action.triggered.connect(lambda checked, t=task: self._move_task(t, 'top'))
            menu.addAction(move_top_action)
            
            move_up_action = QAction("Move Up", self)
            move_up_action.setIcon(icons.get_icon(Icons.PLAY))
            move_up_action.triggered.connect(lambda checked, t=task: self._move_task(t, 'up'))
            menu.addAction(move_up_action)
            
            move_down_action = QAction("Move Down", self)
            move_down_action.setIcon(icons.get_icon(Icons.STOP))
            move_down_action.triggered.connect(lambda checked, t=task: self._move_task(t, 'down'))
            menu.addAction(move_down_action)
            
            move_bottom_action = QAction("Move to Bottom", self)
            move_bottom_action.setIcon(icons.get_icon(Icons.STOP))
            move_bottom_action.triggered.connect(lambda checked, t=task: self._move_task(t, 'bottom'))
            menu.addAction(move_bottom_action)
        
        menu.addSeparator()
        
        speed_action = QAction("Speed Limiter", self)
        speed_action.setIcon(icons.get_icon(Icons.SETTINGS))
        speed_action.setShortcut("Ctrl+L")
        speed_action.triggered.connect(lambda checked, t=task: self._show_speed_limiter(t))
        menu.addAction(speed_action)
        
        menu.addSeparator()
        
        if task.state in [DownloadState.ERROR, DownloadState.CANCELLED]:
            retry_action = QAction("Retry Download", self)
            retry_action.setIcon(icons.get_icon(Icons.PLAY))
            retry_action.setShortcut("Ctrl+R")
            retry_action.triggered.connect(lambda checked, t=task: self._retry_task(t))
            menu.addAction(retry_action)
        
        remove_action = QAction("Delete from List", self)
        remove_action.setIcon(icons.get_icon(Icons.STOP))
        remove_action.setShortcut("Delete")
        remove_action.triggered.connect(lambda checked, t=task: self._remove_task(t))
        menu.addAction(remove_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _toggle_task_pause(self, task):
        """Toggle pause/resume for a task."""
        import asyncio
        if task.state == DownloadState.PAUSED:
            if self._queue:
                asyncio.create_task(self._queue.resume(task.id))
        elif task.state == DownloadState.DOWNLOADING:
            if self._queue:
                asyncio.create_task(self._queue.pause(task.id))
    
    def _show_progress_dialog(self, task):
        """Show progress dialog for a task."""
        if self._parent_window and task:
            from ui.dialogs.download_progress import DownloadProgressDialog
            prog_dlg = DownloadProgressDialog(self._parent_window, task, self._bridge, self._queue)
            prog_dlg.show()
    
    def _open_file(self, task):
        """Open downloaded file."""
        if self._file_opening:
            return
        
        self._file_opening = True
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            from pathlib import Path
            
            if hasattr(task, 'full_path'):
                file_path = Path(task.full_path)
                if file_path.exists():
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.resolve())))
        finally:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self, '_file_opening', False))
    
    def _open_folder(self, task):
        """Open folder containing downloaded file."""
        if self._folder_opening:
            return
        
        self._folder_opening = True
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            from pathlib import Path
            
            if hasattr(task, 'save_path'):
                folder_path = Path(task.save_path)
                if folder_path.is_file():
                    folder_path = folder_path.parent
                if folder_path.exists():
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path.resolve())))
        finally:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self, '_folder_opening', False))
    
    def _copy_url(self, task):
        """Copy download URL to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(task.url)
    
    def _remove_task(self, task):
        """Remove task from queue."""
        import asyncio
        if self._queue:
            asyncio.create_task(self._queue.remove(task.id))
    
    def _retry_task(self, task):
        """Retry a failed download."""
        import asyncio
        if self._queue:
            asyncio.create_task(self._queue.retry(task.id))
    
    def _stop_task(self, task):
        """Force stop a download."""
        import asyncio
        if self._queue:
            asyncio.create_task(self._queue.cancel(task.id))
    
    def _show_properties_window(self, task):
        """Show download properties window."""
        if self._parent_window and task:
            from ui.dialogs.properties_window import PropertiesWindow
            properties_dlg = PropertiesWindow(self._parent_window, task)
            properties_dlg.exec()
    
    def _format_eta(self, seconds):
        """Format ETA in human readable format."""
        if seconds <= 0:
            return "Unknown"
        if seconds < 60:
            return f"{int(seconds)}s"
        m, s = divmod(int(seconds), 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        if h < 24:
            return f"{h}h {m}m"
        d, h = divmod(h, 24)
        return f"{d}d {h}h"
    
    def _move_task(self, task, direction):
        """Move task in queue."""
        import asyncio
        if self._queue:
            if direction == 'top':
                asyncio.create_task(self._queue.move_to_top(task.id))
            elif direction == 'up':
                asyncio.create_task(self._queue.move_up(task.id))
            elif direction == 'down':
                asyncio.create_task(self._queue.move_down(task.id))
    
    def _show_speed_limiter(self, task):
        """Show speed limiter dialog for task."""
        if self._parent_window and task:
            from ui.dialogs.download_progress import DownloadProgressDialog
            prog_dlg = DownloadProgressDialog(self._parent_window, task, self._bridge, self._queue)
            prog_dlg.tabs.setCurrentIndex(1)
            prog_dlg.show()
    
    def _copy_url_with_filename(self, task):
        """Copy URL with filename to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        url_with_filename = f"{task.filename}\n{task.url}"
        clipboard.setText(url_with_filename)
    
    def _open_in_browser(self, task):
        """Open download URL in default browser."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        
        try:
            QDesktopServices.openUrl(QUrl(task.url))
        except Exception:
            pass

    def get_overall_statistics(self) -> dict:
        """Get comprehensive statistics for all downloads."""
        return self._model.get_overall_statistics()
    
    def get_filtered_statistics(self) -> dict:
        """Get statistics for currently filtered view."""
        return self._model.get_filtered_statistics()

    @property
    def download_model(self) -> DownloadModel:
        return self._model
