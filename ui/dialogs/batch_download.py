"""Add multiple downloads from a list of URLs."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)

from qasync import asyncSlot

from config import settings as app_settings
from config.constants import category_for_filename
from core.download_engine import DownloadEngine
from core.protocol_handler import UnsupportedProtocolError, normalize_url
from core.queue_manager import QueueManager
from ui.download_bridge import DownloadBridge


class BatchDownloadDialog(QDialog):
    def __init__(
        self,
        parent,
        engine: DownloadEngine,
        queue: QueueManager,
        bridge: DownloadBridge,
    ):
        super().__init__(parent)
        self._engine = engine
        self._queue = queue
        self._bridge = bridge
        self.setWindowTitle("Batch download")
        self.resize(520, 360)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("One URL per line"))
        self.urls_edit = QTextEdit()
        layout.addWidget(self.urls_edit, stretch=1)

        layout.addWidget(QLabel("Save to"))
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(app_settings.get_download_directory())
        b = QPushButton("Browse…")
        b.clicked.connect(self._browse)
        row.addWidget(self.path_edit)
        row.addWidget(b)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_btn = QPushButton("Add all")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(cancel)
        btn_row.addWidget(self.add_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Download folder", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _on_add(self):
        self._do_add()

    @asyncSlot()
    async def _do_add(self):
        lines = [ln.strip() for ln in self.urls_edit.toPlainText().splitlines() if ln.strip()]
        if not lines:
            QMessageBox.information(self, "Batch", "No URLs entered.")
            return

        save_path = self.path_edit.text().strip() or app_settings.get_download_directory()
        Path(save_path).mkdir(parents=True, exist_ok=True)

        self.add_btn.setEnabled(False)
        errors: list[str] = []
        for raw in lines:
            try:
                url = normalize_url(raw)
            except (UnsupportedProtocolError, ValueError) as e:
                errors.append(f"{raw[:48]}… — {e}")
                continue
            try:
                meta = await self._engine.probe(url)
            except Exception as e:
                errors.append(f"{url[:48]}… — {e}")
                continue
            name = meta["filename"] or "download"
            name = Path(name).name or "download"
            task = self._queue.create_task(
                url=meta["url"],
                filename=name,
                save_path=save_path,
                category=category_for_filename(name),
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
        self.add_btn.setEnabled(True)
        if errors:
            QMessageBox.warning(
                self,
                "Batch complete with errors",
                "\n".join(errors[:12]) + ("\n…" if len(errors) > 12 else ""),
            )
        self.accept()
