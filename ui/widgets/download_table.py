"""
download_table.py - QTableView with custom model backed by QueueManager.
"""

from __future__ import annotations

import humanize
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSlot, QSize
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QTableView, QHeaderView
from utils.icon_manager import icons
from resources.icons.icons import Icons

from config.constants import DownloadState
from core.download_engine import DownloadTask
from core.queue_manager import QueueManager
from ui.download_bridge import DownloadBridge

from .progress_delegate import ProgressDelegate

# Map UI states to SVG icons
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


class DownloadModel(QAbstractTableModel):
    HEADERS = ["", "Filename", "Size", "Progress", "Speed", "ETA", "Category", "Actions"]

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
            if col == 6:
                # Map category to icon
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
                return None # Use DecorationRole for column 0
            if col == 1:
                return task.filename
            if col == 2:
                if task.total_size > 0:
                    return humanize.naturalsize(task.total_size, binary=True)
                return "—"
            if col == 3:
                return round(task.progress, 2)
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
                return task.category
            if col == 7:
                return self._action_text(st)
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return QColor(STATE_COLORS.get(st, "#8b949e"))
            if col == 4 and st == "dl":
                return QColor("#58a6ff")
            if col == 6:
                return QColor(CAT_COLORS.get(task.category, "#8b949e"))
        if role == Qt.ItemDataRole.BackgroundRole:
            if col == 0:
                return QColor(STATE_BG_COLORS.get(st, "transparent"))
            if col == 6:
                return QColor(CAT_BG_COLORS.get(task.category, "transparent"))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def _action_text(self, state: str) -> str:
        return "⚙" # Placeholder for actions column until we have a proper delegate

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
        self.setColumnWidth(3, 130)
        self.setColumnWidth(4, 90)
        self.setColumnWidth(5, 80)
        self.progress_delegate = ProgressDelegate()
        self.setItemDelegateForColumn(3, self.progress_delegate)

    @property
    def download_model(self) -> DownloadModel:
        return self._model
