"""Qt signals for download lifecycle (main thread)."""

from PyQt6.QtCore import QObject, pyqtSignal


class DownloadBridge(QObject):
    """Emitted from asyncio callbacks; receivers run on GUI thread."""

    tasks_changed = pyqtSignal()
    stats_changed = pyqtSignal()
    task_progress = pyqtSignal(str)
    pause_resume_requested = pyqtSignal(str)
