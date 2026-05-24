"""
download_progress.py - Active download status dialog (IDM style).
Complete with working progress bar, speed limiter, and post‑download actions.
"""
import os
import humanize
import asyncio
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTabWidget, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSlider, QSpinBox, QCheckBox, QGroupBox
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from core.download_engine import DownloadTask, DownloadState
from ui.download_bridge import DownloadBridge


class DownloadProgressDialog(QDialog):
    speed_limit_changed = pyqtSignal(int)

    def __init__(self, parent, task: DownloadTask, bridge: DownloadBridge, queue_manager=None):
        super().__init__(parent)
        self.task = task
        self.bridge = bridge
        self.queue_manager = queue_manager
        self._completion_executed = False

        if not self.task.progress_callback:
            def _progress_callback(t):
                self.bridge.task_progress.emit(t.id)
            self.task.progress_callback = _progress_callback

        if not self.task.state_callback:
            def _state_callback(t):
                self.bridge.tasks_changed.emit()
            self.task.state_callback = _state_callback

        self.setWindowTitle(f"{int(task.progress)}% {task.filename}")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)

        self._setup_ui()

        self.bridge.task_progress.connect(self._on_progress)
        self.bridge.tasks_changed.connect(self._on_state_changed)

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(1000)

        self._update_button_states()
        self._refresh_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)

        self.url_label = QLabel(self.task.url)
        self.url_label.setWordWrap(True)
        self.url_label.setStyleSheet("color: #58a6ff; font-size: 11px;")
        status_layout.addWidget(self.url_label)

        info_grid = QVBoxLayout()
        self.status_lbl   = QLabel(f"Status: {self.task.state}")
        self.size_lbl     = QLabel(f"File size: {humanize.naturalsize(self.task.total_size, binary=True)}")
        self.downloaded_lbl = QLabel(
            f"Downloaded: {humanize.naturalsize(self.task.downloaded, binary=True)} "
            f"({self.task.progress:.2f}%)"
        )
        self.speed_lbl    = QLabel(f"Transfer rate: {humanize.naturalsize(self.task.speed, binary=True)}/sec")
        self.eta_lbl      = QLabel(f"Time left: {self._fmt_eta(self.task.eta)}")
        self.resume_lbl   = QLabel("Resume capability: Yes")
        self.error_lbl    = QLabel("")

        for lbl in (self.status_lbl, self.size_lbl, self.downloaded_lbl,
                    self.speed_lbl, self.eta_lbl, self.resume_lbl, self.error_lbl):
            lbl.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px;")
            info_grid.addWidget(lbl)
        status_layout.addLayout(info_grid)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.task.progress))
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #30363d;
                height: 25px;
                background: #161b22;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1f6feb, stop:1 #58a6ff);
            }
        """)
        status_layout.addWidget(self.progress_bar)

        status_layout.addWidget(QLabel("Start positions and download progress by connections"))
        self.conn_table = QTableWidget()
        self.conn_table.setColumnCount(4)
        self.conn_table.setHorizontalHeaderLabels(["Segment", "Range", "Downloaded", "Status"])
        self.conn_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.conn_table.setFixedHeight(150)
        status_layout.addWidget(self.conn_table)

        speed_tab = QWidget()
        speed_layout = QVBoxLayout(speed_tab)
        grp = QGroupBox("Download Speed Limit (kB/s)")
        grp_layout = QVBoxLayout()
        slider_row = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 10000)
        self.speed_slider.setTickInterval(1000)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setRange(0, 10000)
        self.speed_spinbox.setSuffix(" kB/s")
        self.speed_spinbox.setSpecialValueText("Unlimited")
        self.speed_slider.valueChanged.connect(self.speed_spinbox.setValue)
        self.speed_spinbox.valueChanged.connect(self.speed_slider.setValue)
        slider_row.addWidget(QLabel("0"))
        slider_row.addWidget(self.speed_slider)
        slider_row.addWidget(self.speed_spinbox)
        grp_layout.addLayout(slider_row)

        btn_row = QHBoxLayout()
        self.apply_speed_btn = QPushButton("Apply")
        self.reset_speed_btn = QPushButton("Reset to Unlimited")
        self.apply_speed_btn.clicked.connect(self._apply_speed_limit)
        self.reset_speed_btn.clicked.connect(lambda: self.speed_spinbox.setValue(0))
        btn_row.addStretch()
        btn_row.addWidget(self.apply_speed_btn)
        btn_row.addWidget(self.reset_speed_btn)
        grp_layout.addLayout(btn_row)
        grp.setLayout(grp_layout)
        speed_layout.addWidget(grp)
        speed_layout.addStretch()

        completion_tab = QWidget()
        comp_layout = QVBoxLayout(completion_tab)
        self.open_file_cb   = QCheckBox("Open file when finished")
        self.open_folder_cb = QCheckBox("Open containing folder when finished")
        self.shutdown_cb    = QCheckBox("Shut down computer when all downloads complete")
        self.open_file_cb.setChecked(False)
        self.open_folder_cb.setChecked(False)
        self.shutdown_cb.setChecked(False)
        comp_layout.addWidget(self.open_file_cb)
        comp_layout.addWidget(self.open_folder_cb)
        comp_layout.addWidget(self.shutdown_cb)
        comp_layout.addStretch()

        self.tabs.addTab(status_tab, "Download status")
        self.tabs.addTab(speed_tab, "Speed Limiter")
        self.tabs.addTab(completion_tab, "Options on completion")

        btn_layout = QHBoxLayout()
        self.details_btn   = QPushButton("<< Hide details")
        self.pause_btn     = QPushButton("Pause")
        self.cancel_btn    = QPushButton("Cancel")
        self.open_btn      = QPushButton("Open File")
        self.open_folder_btn = QPushButton("Open Folder")

        btn_style = """
            QPushButton {
                padding: 6px 12px; border: 1px solid
                background-color:
            }
            QPushButton:hover { background-color:
            QPushButton:pressed { background-color:
            QPushButton:disabled { background-color:
        """
        for b in (self.details_btn, self.pause_btn, self.cancel_btn,
                  self.open_btn, self.open_folder_btn):
            b.setStyleSheet(btn_style)

        self.pause_btn.clicked.connect(self._toggle_pause)
        self.cancel_btn.clicked.connect(self._cancel_download)
        self.open_btn.clicked.connect(self._open_file)
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.details_btn.clicked.connect(self._toggle_details)

        self.open_btn.setVisible(False)
        self.open_folder_btn.setVisible(False)

        btn_layout.addWidget(self.details_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _fmt_eta(self, seconds):
        if seconds <= 0:
            return "Unknown"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s} sec"

    def _get_current_task(self):
        if self.queue_manager:
            task = self.queue_manager._find(self.task.id)
            if task:
                return task
        return self.task

    @pyqtSlot(str)
    def _on_progress(self, tid):
        """Handle progress signal (explicit string slot)."""
        if tid != self.task.id:
            return
        current_task = self._get_current_task()
        if current_task:
            self.task = current_task
            self.progress_bar.setValue(int(self.task.progress))
            self.setWindowTitle(f"{int(self.task.progress)}% {self.task.filename}")
            self._refresh_stats()

    def _refresh_stats(self):
        """Periodic refresh – also used by the 1‑second timer."""
        current_task = self._get_current_task()
        if current_task:
            self.task = current_task

        self.progress_bar.setValue(int(self.task.progress))

        self.status_lbl.setText(f"Status: {self.task.state.title()}")
        self.size_lbl.setText(f"File size: {humanize.naturalsize(self.task.total_size, binary=True)}")
        self.downloaded_lbl.setText(
            f"Downloaded: {humanize.naturalsize(self.task.downloaded, binary=True)} "
            f"({self.task.progress:.2f}%)"
        )
        self.speed_lbl.setText(
            f"Transfer rate: {humanize.naturalsize(self.task.speed, binary=True)}/sec"
        )
        self.eta_lbl.setText(f"Time left: {self._fmt_eta(self.task.eta)}")

        if hasattr(self.task, 'supports_resume'):
            self.resume_lbl.setText(
                f"Resume capability: {'Yes' if self.task.supports_resume else 'No'}"
            )
        else:
            self.resume_lbl.setText("Resume capability: Unknown")

        if self.task.state == DownloadState.ERROR and self.task.error:
            self.error_lbl.setText(f"Error: {self.task.error}")
            self.error_lbl.setStyleSheet("color: #f85149; font-size: 12px;")
        else:
            self.error_lbl.setText("")
            self.error_lbl.setStyleSheet("")

        self._update_connection_table()

        self.setWindowTitle(f"{int(self.task.progress)}% {self.task.filename}")
        if self.task.state == DownloadState.COMPLETED:
            self.setWindowTitle(f"100% {self.task.filename} - Completed")
        elif self.task.state == DownloadState.ERROR:
            self.setWindowTitle(f"Error {self.task.filename}")
        elif self.task.state == DownloadState.CANCELLED:
            self.setWindowTitle(f"Cancelled {self.task.filename}")

    def _on_state_changed(self):
        self._update_button_states()
        self._refresh_stats()
        if self.task.state == DownloadState.COMPLETED:
            self._execute_completion_options()

    def _update_button_states(self):
        state = self.task.state
        if state == DownloadState.PAUSED:
            self.pause_btn.setText("Resume")
            self.pause_btn.setEnabled(True)
            self.open_btn.setVisible(False)
            self.open_folder_btn.setVisible(False)
        elif state in (DownloadState.DOWNLOADING, DownloadState.QUEUED):
            self.pause_btn.setText("Pause")
            self.pause_btn.setEnabled(True)
            self.open_btn.setVisible(False)
            self.open_folder_btn.setVisible(False)
        elif state == DownloadState.COMPLETED:
            self.pause_btn.setText("Completed")
            self.pause_btn.setEnabled(False)
            self.open_btn.setVisible(True)
            self.open_folder_btn.setVisible(True)
            self.cancel_btn.setText("Close")
        elif state == DownloadState.ERROR:
            self.pause_btn.setText("Error")
            self.pause_btn.setEnabled(False)
            self.open_btn.setVisible(False)
            self.open_folder_btn.setVisible(True)
            self.cancel_btn.setText("Close")
        elif state == DownloadState.CANCELLED:
            self.pause_btn.setText("Cancelled")
            self.pause_btn.setEnabled(False)
            self.open_btn.setVisible(False)
            self.open_folder_btn.setVisible(False)
            self.cancel_btn.setText("Close")

    def _toggle_pause(self):
        if self.queue_manager:
            if self.task.state == DownloadState.PAUSED:
                asyncio.create_task(self.queue_manager.resume(self.task.id))
            elif self.task.state in (DownloadState.DOWNLOADING, DownloadState.QUEUED):
                asyncio.create_task(self.queue_manager.pause(self.task.id))
        else:
            self.bridge.pause_resume_requested.emit(self.task.id)

    def _cancel_download(self):
        if self.task.state in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR):
            self.reject()
            return
            
        if self.queue_manager:
            asyncio.create_task(self.queue_manager.cancel(self.task.id))
        self.reject()

    def _open_file(self):
        full = getattr(self.task, 'full_path', None)
        if full and Path(full).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(full).resolve())))

    def _open_folder(self):
        save = getattr(self.task, 'save_path', None)
        if save:
            folder = Path(save)
            if folder.is_file():
                folder = folder.parent
            if folder.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def _toggle_details(self):
        visible = self.conn_table.isVisible()
        self.conn_table.setVisible(not visible)
        self.details_btn.setText("<< Hide details" if not visible else ">> Show details")

    def _apply_speed_limit(self):
        """Emit signal with chosen limit in kB/s."""
        limit = self.speed_spinbox.value()
        self.speed_limit_changed.emit(limit)

    def _execute_completion_options(self):
        """Run selected post‑download actions."""
        if self._completion_executed:
            return
        self._completion_executed = True
        
        if self.open_file_cb.isChecked():
            self._open_file()
        if self.open_folder_cb.isChecked():
            self._open_folder()
        if self.shutdown_cb.isChecked():
            self._shutdown_system()

    def _shutdown_system(self):
        """Platform‑aware shutdown command."""
        try:
            import platform
            system = platform.system()
            if system == "Windows":
                os.system("shutdown /s /t 10")
            elif system == "Linux" or system == "Darwin":
                os.system("sudo shutdown -h +1")
        except Exception as e:
            print(f"Shutdown failed: {e}")

    def _update_connection_table(self):
        self.conn_table.setUpdatesEnabled(False)
        self.conn_table.setRowCount(0)

        if not self.task.segments:
            self.conn_table.setRowCount(1)
            self.conn_table.setItem(0, 0, QTableWidgetItem("1"))
            start = 0
            end = self.task.total_size - 1 if self.task.total_size > 0 else "?"
            self.conn_table.setItem(0, 1, QTableWidgetItem(f"{start} - {end}"))
            self.conn_table.setItem(0, 2, QTableWidgetItem(
                humanize.naturalsize(self.task.downloaded, binary=True))
            )
            self.conn_table.setItem(0, 3, QTableWidgetItem(self.task.state.title()))
            self.conn_table.setUpdatesEnabled(True)
            return

        self.conn_table.setRowCount(len(self.task.segments))
        for i, seg in enumerate(self.task.segments):
            self.conn_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            range_text = f"{seg.start} - {seg.end if seg.end > 0 else '?'}"
            self.conn_table.setItem(i, 1, QTableWidgetItem(range_text))
            self.conn_table.setItem(i, 2, QTableWidgetItem(
                humanize.naturalsize(seg.downloaded, binary=True))
            )
            if seg.complete:
                status = "Completed"
            elif seg.downloaded > 0:
                status = f"Downloading ({seg.downloaded} bytes)"
            else:
                status = "Waiting"
            self.conn_table.setItem(i, 3, QTableWidgetItem(status))
        self.conn_table.setUpdatesEnabled(True)