"""Application preferences — tabbed: General, Bandwidth & schedule, Clipboard & appearance."""

from collections.abc import Callable

from PyQt6.QtCore import QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFileDialog,
    QTabWidget,
    QWidget,
    QFormLayout,
    QTimeEdit,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QStyle,
    QSlider,
)
from utils.icon_manager import icons
from resources.icons.icons import Icons

from config import settings as app_settings
from utils.sound_manager import get_sound_manager
from core.download_engine import DownloadEngine
from core.queue_manager import QueueManager


def _time_from_string(hhmm: str) -> QTime:
    parts = (hhmm or "00:00").replace(".", ":").split(":")
    h = max(0, min(23, int(parts[0])))
    m = max(0, min(59, int(parts[1]) if len(parts) > 1 else 0))
    return QTime(h, m)


class PreferencesDialog(QDialog):
    def __init__(
        self,
        parent,
        engine: DownloadEngine,
        queue: QueueManager,
        on_saved: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self._engine = engine
        self._queue = queue
        self._on_saved = on_saved
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(440)
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout = QVBoxLayout(self)

        layout.addWidget(self._tabs)

        self._build_general_tab()
        self._build_file_types_tab()
        self._build_save_to_tab()
        self._build_downloads_tab()
        self._build_connection_tab()
        self._build_proxy_tab()
        self._build_site_logins_tab()
        self._build_dial_up_tab()
        self._build_sounds_tab()
        self._build_ui_tab()

        self._tabs.setTabIcon(0, icons.get_icon(Icons.SETTINGS))
        self._tabs.setTabIcon(1, icons.get_icon(Icons.FILE))
        self._tabs.setTabIcon(2, icons.get_icon(Icons.FOLDER))
        self._tabs.setTabIcon(3, icons.get_icon(Icons.DOWNLOAD))
        self._tabs.setTabIcon(4, icons.get_icon(Icons.WIFI))
        self._tabs.setTabIcon(5, icons.get_icon(Icons.PROXY))
        self._tabs.setTabIcon(6, icons.get_icon(Icons.LOCK))
        self._tabs.setTabIcon(7, icons.get_icon(Icons.GLOBE))
        self._tabs.setTabIcon(8, icons.get_icon(Icons.NOTIFICATION))
        self._tabs.setTabIcon(9, icons.get_icon(Icons.VIEW_GRID))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setIcon(icons.get_icon(Icons.STOP))
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Save")
        ok.setIcon(icons.get_icon(Icons.STATUS_COMPLETE))
        ok.setObjectName("primary")
        ok.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _build_general_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        integration_label = QLabel("Browser/System Integration")
        integration_label.setStyleSheet("font-weight: bold; border-bottom: 1px solid #30363d;")
        layout.addWidget(integration_label)

        self.launch_startup = QCheckBox("Launch Spider Manager on startup")
        self.launch_startup.setChecked(app_settings.get_launch_on_startup())
        layout.addWidget(self.launch_startup)

        self.auto_clipboard = QCheckBox("Automatically start downloading of URLs placed to clipboard")
        self.auto_clipboard.setChecked(app_settings.get_clipboard_monitor())
        layout.addWidget(self.auto_clipboard)

        capture_group = QGroupBox("Capture downloads from the following browsers:")
        capture_layout = QVBoxLayout(capture_group)
        
        self.browser_list = QListWidget()
        browsers = ["Apple Safari", "Google Chrome", "Internet Explorer", "Microsoft Edge", 
                    "Microsoft Edge Legacy", "Mozilla Firefox", "Opera"]
        for browser in browsers:
            item = QListWidgetItem(browser)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.browser_list.addItem(item)
        capture_layout.addWidget(self.browser_list)

        add_browser_btn = QPushButton("Add browser...")
        add_browser_btn.setIcon(icons.get_icon(Icons.ADD))
        capture_layout.addWidget(add_browser_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(capture_group)

        actions_form = QFormLayout()
        
        btn_keys = QPushButton("Keys...")
        btn_keys.setIcon(icons.get_icon(Icons.KEY))
        actions_form.addRow("Customize keys to prevent or force downloading:", btn_keys)
        
        btn_menu = QPushButton("Edit...")
        btn_menu.setIcon(icons.get_icon(Icons.OPTIONS_DOTS))
        actions_form.addRow("Customize menu items in context menu of browsers:", btn_menu)
        
        btn_panels = QPushButton("Edit...")
        btn_panels.setIcon(icons.get_icon(Icons.VIEW_LIST))
        actions_form.addRow("Customize Download panels in browsers:", btn_panels)
        
        layout.addLayout(actions_form)

        self._tabs.addTab(w, "General")

    def _build_file_types_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self.ext_edit = QTextEdit()
        self.ext_edit.setPlainText(app_settings.get_auto_file_types())
        self.ext_edit.setPlaceholderText("3GP 7Z AAC ACE AIF ARJ ASF ASPX AVI BIN GZ GZIP IMG ISO LZH M4A M4V MKV MOV MP3 MP4 MPA MPE MPEG MPG MSI MSU OGG OGV PDF RA RAR RM RMVB SEA SIT SITX TAR TAZ TGZ TS VOB WAV WMA WMV Z ZIP")
        form.addRow("Automatically start downloading the following file types:", self.ext_edit)
        
        self.ignore_sites = QTextEdit()
        self.ignore_sites.setPlainText(app_settings.get_ignore_sites())
        form.addRow("Don't start downloading automatically from the following sites:", self.ignore_sites)
        self._tabs.addTab(w, "File types")

    def _build_save_to_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        
        cat_combo = QComboBox()
        cat_combo.addItems(["General", "Compressed", "Documents", "Music", "Programs", "Video"])
        form.addRow("Category:", cat_combo)
        
        self.path_label = QLabel(app_settings.get_download_directory())
        self.path_label.setStyleSheet("border: 1px solid #30363d; padding: 4px;")
        browse = QPushButton("Browse...")
        browse.setIcon(icons.get_icon(Icons.FOLDER_OPEN))
        browse.clicked.connect(self._browse)
        form.addRow("Default download directory for 'General' category:", self.path_label)
        form.addRow("", browse)
        
        self.temp_path_label = QLabel(app_settings.get_temp_directory())
        self.temp_path_label.setStyleSheet("border: 1px solid #30363d; padding: 4px;")
        form.addRow("Temporary directory:", self.temp_path_label)
        btn_temp_browse = QPushButton("Browse...")
        btn_temp_browse.setIcon(icons.get_icon(Icons.FOLDER_OPEN))
        form.addRow("", btn_temp_browse)
        
        self._tabs.addTab(w, "Save to")

    def _build_downloads_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        
        self.show_start_diag = QCheckBox("Show start download dialog")
        self.show_start_diag.setChecked(app_settings.get_show_start_dialog())
        form.addRow(self.show_start_diag)
        
        self.show_compl_diag = QCheckBox("Show download complete dialog")
        self.show_compl_diag.setChecked(app_settings.get_show_complete_dialog())
        form.addRow(self.show_compl_diag)
        
        self.speed_limit_enabled = QCheckBox("Enable Speed Limiter")
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 999999)
        self.speed_limit_spin.setSuffix(" KB/s")
        self.speed_limit_spin.setValue(app_settings.get_speed_limit_kb())
        form.addRow(self.speed_limit_enabled, self.speed_limit_spin)
        
        self._tabs.addTab(w, "Downloads")

    def _build_connection_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 32)
        self.segments_spin.setValue(app_settings.get_segment_count())
        form.addRow("Segments per file:", self.segments_spin)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(app_settings.get_max_concurrent())
        form.addRow("Max concurrent:", self.concurrent_spin)
        
        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 99)
        self.retry_count.setValue(5)
        form.addRow("Max retries on error:", self.retry_count)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setValue(30)
        form.addRow("Connection timeout:", self.timeout_spin)
        
        self._tabs.addTab(w, "Connection")

    def _build_proxy_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self.proxy_mode_combo = QComboBox()
        self.proxy_mode_combo.addItem("No proxy", "none")
        self.proxy_mode_combo.addItem("Use system settings", "system")
        self.proxy_mode_combo.addItem("Manual proxy configuration", "manual")
        current_mode = app_settings.get_proxy_mode()
        for i in range(self.proxy_mode_combo.count()):
            if self.proxy_mode_combo.itemData(i) == current_mode:
                self.proxy_mode_combo.setCurrentIndex(i)
                break
        form.addRow("Proxy configuration:", self.proxy_mode_combo)

        self.proxy_host_edit = QLineEdit(app_settings.get_proxy_host())
        self.proxy_host_edit.setPlaceholderText("proxy.example.com")
        form.addRow("Host:", self.proxy_host_edit)

        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setRange(0, 65535)
        self.proxy_port_spin.setValue(app_settings.get_proxy_port())
        form.addRow("Port:", self.proxy_port_spin)

        self.proxy_user_edit = QLineEdit(app_settings.get_proxy_user())
        form.addRow("Username (optional):", self.proxy_user_edit)

        self.proxy_password_edit = QLineEdit(app_settings.get_proxy_password())
        self.proxy_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password (optional):", self.proxy_password_edit)

        def _toggle_manual_fields():
            manual = self.proxy_mode_combo.currentData() == "manual"
            self.proxy_host_edit.setEnabled(manual)
            self.proxy_port_spin.setEnabled(manual)
            self.proxy_user_edit.setEnabled(manual)
            self.proxy_password_edit.setEnabled(manual)

        self.proxy_mode_combo.currentIndexChanged.connect(lambda _i: _toggle_manual_fields())
        _toggle_manual_fields()

        self._tabs.addTab(w, "Proxy / Socks")

    def _build_site_logins_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Site specific logins and passwords:"))
        logins_list = QListWidget()
        layout.addWidget(logins_list)
        btn_row = QHBoxLayout()
        btn_new = QPushButton("New")
        btn_new.setIcon(icons.get_icon(Icons.ADD))
        btn_row.addWidget(btn_new)
        
        btn_edit = QPushButton("Edit")
        btn_edit.setIcon(icons.get_icon(Icons.OPTIONS_DOTS))
        btn_row.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete")
        btn_delete.setIcon(icons.get_icon(Icons.DELETE))
        btn_row.addWidget(btn_delete)
        
        layout.addLayout(btn_row)
        self._tabs.addTab(w, "Site Logins")

    def _build_dial_up_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.addRow(QCheckBox("Use Windows Dial-Up Networking"))
        self._tabs.addTab(w, "Dial Up / VPN")

    def _build_sounds_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        master_group = QGroupBox("Master Settings")
        master_layout = QFormLayout(master_group)
        
        self.sound_enabled_master = QCheckBox("Enable sound notifications")
        self.sound_enabled_master.setChecked(app_settings.get_sound_notifications_enabled())
        master_layout.addRow(self.sound_enabled_master)
        
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Master Volume:")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(app_settings.get_master_volume() * 100))
        self.volume_label = QLabel(f"{int(app_settings.get_master_volume() * 100)}%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        master_layout.addRow("Volume:", volume_layout)
        
        layout.addWidget(master_group)
        
        events_group = QGroupBox("Event Sounds")
        events_layout = QFormLayout(events_group)
        
        self.sound_checkboxes = {}
        self.sound_path_labels = {}
        self.sound_browse_buttons = {}
        self.sound_play_buttons = {}
        
        events = [
            ("download_complete", "Download Complete"),
            ("download_failed", "Download Failed"),
            ("queue_finished", "Queue Finished")
        ]
        
        for event_key, event_name in events:
            row = QHBoxLayout()
            
            checkbox = QCheckBox(event_name)
            checkbox.setChecked(app_settings.get_sound_enabled(event_key))
            self.sound_checkboxes[event_key] = checkbox
            row.addWidget(checkbox)
            
            path_label = QLabel(app_settings.get_sound_path(event_key))
            path_label.setVisible(False)
            self.sound_path_labels[event_key] = path_label
            row.addWidget(path_label)
            
            browse_btn = QPushButton("Browse...")
            browse_btn.setIcon(icons.get_icon(Icons.FOLDER_OPEN))
            browse_btn.clicked.connect(lambda checked, k=event_key: self._browse_sound(k))
            self.sound_browse_buttons[event_key] = browse_btn
            row.addWidget(browse_btn)
            
            play_btn = QPushButton("Play")
            play_btn.setIcon(icons.get_icon(Icons.PLAY))
            play_btn.clicked.connect(lambda checked, k=event_key: self._play_sound(k))
            self.sound_play_buttons[event_key] = play_btn
            row.addWidget(play_btn)
            
            events_layout.addRow(row)
        
        layout.addWidget(events_group)
        layout.addStretch()
        
        self._tabs.addTab(w, "Sounds")
    
    def _browse_sound(self, event_key: str):
        """Open file dialog to select sound file for an event."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Sound Files (*.wav *.mp3 *.ogg *.flac);;All Files (*)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                sound_path = selected_files[0]
                self.sound_path_labels[event_key].setText(sound_path)
    
    def _play_sound(self, event_key: str):
        """Preview the sound for an event."""
        sound_path = self.sound_path_labels[event_key].text()
        if sound_path:
            sound_manager = get_sound_manager()
            sound_manager.play_preview(sound_path)
        else:
            sound_path = app_settings.get_sound_path(event_key)
            if sound_path:
                sound_manager = get_sound_manager()
                sound_manager.play_preview(sound_path)

    def _build_ui_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        idx = 0 if app_settings.get_ui_theme() == "dark" else 1
        self.theme_combo.setCurrentIndex(idx)
        form.addRow("Interface Theme:", self.theme_combo)
        
        self.tray_min = QCheckBox("Minimize to system tray")
        self.tray_min.setChecked(True)
        form.addRow(self.tray_min)
        
        self.close_min = QCheckBox("Close to system tray")
        self.close_min.setChecked(True)
        form.addRow(self.close_min)

        self._tabs.addTab(w, "Appearance")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Download folder", self.path_label.text())
        if d:
            self.path_label.setText(d)

    def _save(self):
        app_settings.set_launch_on_startup(self.launch_startup.isChecked())
        app_settings.set_clipboard_monitor(self.auto_clipboard.isChecked())
        
        app_settings.set_auto_file_types(self.ext_edit.toPlainText())
        app_settings.set_ignore_sites(self.ignore_sites.toPlainText())
        
        app_settings.set_download_directory(self.path_label.text())
        app_settings.set_temp_directory(self.temp_path_label.text())
        
        app_settings.set_show_start_dialog(self.show_start_diag.isChecked())
        app_settings.set_show_complete_dialog(self.show_compl_diag.isChecked())
        
        speed_kb = self.speed_limit_spin.value()
        app_settings.set_speed_limit_kb(speed_kb)
        
        app_settings.set_segment_count(self.segments_spin.value())
        app_settings.set_max_concurrent(self.concurrent_spin.value())

        proxy_mode = self.proxy_mode_combo.currentData()
        app_settings.set_proxy_mode(proxy_mode if isinstance(proxy_mode, str) else "none")
        app_settings.set_proxy_host(self.proxy_host_edit.text().strip())
        app_settings.set_proxy_port(self.proxy_port_spin.value())
        app_settings.set_proxy_user(self.proxy_user_edit.text().strip())
        app_settings.set_proxy_password(self.proxy_password_edit.text())

        theme_data = self.theme_combo.currentData(Qt.ItemDataRole.UserRole)
        app_settings.set_ui_theme(theme_data if isinstance(theme_data, str) else "dark")
        
        app_settings.set_sound_notifications_enabled(self.sound_enabled_master.isChecked())
        app_settings.set_master_volume(self.volume_slider.value() / 100.0)
        
        for event_key in ["download_complete", "download_failed", "queue_finished"]:
            app_settings.set_sound_enabled(event_key, self.sound_checkboxes[event_key].isChecked())
            app_settings.set_sound_path(event_key, self.sound_path_labels[event_key].text())
        
        sound_manager = get_sound_manager()
        sound_manager.set_volume(self.volume_slider.value() / 100.0)
        for event_key in ["download_complete", "download_failed", "queue_finished"]:
            sound_manager.set_event_enabled(event_key, self.sound_checkboxes[event_key].isChecked())
            if self.sound_path_labels[event_key].text():
                sound_manager.set_sound_path(event_key, self.sound_path_labels[event_key].text())
        
        self._engine.segments = app_settings.get_segment_count()
        self._queue.set_max_concurrent(app_settings.get_max_concurrent())
        self._engine.speed_limiter.set_limit_bps(app_settings.get_speed_limit_kb() * 1024)

        if self._on_saved:
            self._on_saved()

        self.accept()
