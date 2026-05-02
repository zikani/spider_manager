"""Add single download: probe URL and enqueue."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from utils.icon_manager import icons
from resources.icons.icons import Icons

from qasync import asyncSlot

from config import settings as app_settings
from core.download_engine import DownloadEngine
from core.protocol_handler import UnsupportedProtocolError, normalize_url
from core.queue_manager import QueueManager
from ui.download_bridge import DownloadBridge
from utils.file_utils import sanitize_filename
from utils.mime_detector import category_from_metadata


class AddDownloadDialog(QDialog):
    def __init__(
        self,
        parent,
        engine: DownloadEngine,
        queue: QueueManager,
        bridge: DownloadBridge,
        initial_url: str = "",
    ):
        super().__init__(parent)
        self._engine = engine
        self._queue = queue
        self._bridge = bridge
        self._initial_url = (initial_url or "").strip()
        self.setWindowTitle("Add download")
        self.setMinimumWidth(480)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://…")
        if self._initial_url:
            self.url_edit.setText(self._initial_url)
        layout.addWidget(self.url_edit)

        layout.addWidget(QLabel("Save to"))
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(app_settings.get_download_directory())
        browse = QPushButton("Browse…")
        browse.setIcon(icons.get_icon(Icons.FOLDER_OPEN))
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse)
        layout.addLayout(path_row)

        layout.addWidget(QLabel("Filename (optional)"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setIcon(icons.get_icon(Icons.STOP))
        cancel.clicked.connect(self.reject)
        self.ok_btn = QPushButton("Add")
        self.ok_btn.setIcon(icons.get_icon(Icons.ADD))
        self.ok_btn.setObjectName("primary")
        self.ok_btn.clicked.connect(self._on_add_clicked)
        btn_row.addWidget(cancel)
        btn_row.addWidget(self.ok_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Download folder", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _on_add_clicked(self):
        self._do_add()

    @asyncSlot()
    async def _do_add(self):
        raw = self.url_edit.text().strip()
        try:
            url = normalize_url(raw)
        except UnsupportedProtocolError as e:
            QMessageBox.warning(self, "Unsupported URL", str(e))
            return
        except ValueError as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        save_path = self.path_edit.text().strip() or app_settings.get_download_directory()
        Path(save_path).mkdir(parents=True, exist_ok=True)

        self.ok_btn.setEnabled(False)
        try:
            meta = await self._engine.probe(url)
        except Exception as e:
            QMessageBox.warning(self, "Probe failed", str(e))
            self.ok_btn.setEnabled(True)
            return

        raw_name = self.name_edit.text().strip() or meta["filename"] or "download"
        name = sanitize_filename(Path(raw_name).name)

        task = self._queue.create_task(
            url=meta["url"],
            filename=name,
            save_path=save_path,
            category=category_from_metadata(name, meta.get("content_type")),
        )
        task.total_size = int(meta.get("size") or 0)

        def _pc(t):
            self._bridge.task_progress.emit(t.id)

        def _sc(_t):
            self._bridge.tasks_changed.emit()
            self._bridge.stats_changed.emit()

        task.progress_callback = _pc
        task.state_callback = _sc

        await self._queue.add(task)
        self._bridge.tasks_changed.emit()
        self._bridge.stats_changed.emit()
        self.ok_btn.setEnabled(True)
        self.accept()
