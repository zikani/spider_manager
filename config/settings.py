"""
User preferences via QSettings (JSON-compatible IniFormat on Windows).
"""

import os
from pathlib import Path

from PyQt6.QtCore import QSettings

from config.constants import DEFAULT_CONCURRENT, DEFAULT_SEGMENTS


_ORG = "SpiderManager"
_APP = "Spider"


def _settings() -> QSettings:
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, _ORG, _APP)


def default_download_dir() -> str:
    return str(Path.home() / "Downloads")


def get_download_directory() -> str:
    s = _settings()
    path = s.value("download_directory", default_download_dir(), type=str)
    return path if path else default_download_dir()


def set_download_directory(path: str) -> None:
    s = _settings()
    s.setValue("download_directory", path)


def get_segment_count() -> int:
    s = _settings()
    n = int(s.value("segment_count", DEFAULT_SEGMENTS))
    return max(1, min(32, n))


def set_segment_count(n: int) -> None:
    _settings().setValue("segment_count", max(1, min(32, n)))


def get_max_concurrent() -> int:
    s = _settings()
    n = int(s.value("max_concurrent", DEFAULT_CONCURRENT))
    return max(1, min(10, n))


def set_max_concurrent(n: int) -> None:
    _settings().setValue("max_concurrent", max(1, min(10, n)))


def get_speed_limit_kb() -> int:
    s = _settings()
    v = int(s.value("speed_limit_kb", 0))
    return max(0, min(999_999, v))


def set_speed_limit_kb(kb: int) -> None:
    _settings().setValue("speed_limit_kb", max(0, min(999_999, kb)))


def get_scheduler_enabled() -> bool:
    return bool(_settings().value("scheduler_enabled", False))


def set_scheduler_enabled(enabled: bool) -> None:
    _settings().setValue("scheduler_enabled", bool(enabled))


def get_scheduler_start() -> str:
    return _settings().value("scheduler_start", "", type=str) or ""


def set_scheduler_start(value: str) -> None:
    _settings().setValue("scheduler_start", value or "")


def get_scheduler_end() -> str:
    return _settings().value("scheduler_end", "", type=str) or ""


def set_scheduler_end(value: str) -> None:
    _settings().setValue("scheduler_end", value or "")


def get_clipboard_monitor() -> bool:
    return bool(_settings().value("clipboard_monitor", False))


def set_clipboard_monitor(enabled: bool) -> None:
    _settings().setValue("clipboard_monitor", bool(enabled))


def get_ui_theme() -> str:
    v = (_settings().value("ui_theme", "dark", type=str) or "dark").lower()
    return v if v in ("dark", "light") else "dark"


def set_ui_theme(theme: str) -> None:
    t = (theme or "dark").lower()
    _settings().setValue("ui_theme", t if t in ("dark", "light") else "dark")


def get_launch_on_startup() -> bool:
    return bool(_settings().value("launch_on_startup", False))


def set_launch_on_startup(enabled: bool) -> None:
    _settings().setValue("launch_on_startup", bool(enabled))


def get_show_start_dialog() -> bool:
    return bool(_settings().value("show_start_dialog", True))


def set_show_start_dialog(enabled: bool) -> None:
    _settings().setValue("show_start_dialog", bool(enabled))


def get_show_complete_dialog() -> bool:
    return bool(_settings().value("show_complete_dialog", True))


def set_show_complete_dialog(enabled: bool) -> None:
    _settings().setValue("show_complete_dialog", bool(enabled))


def get_auto_file_types() -> str:
    return _settings().value("auto_file_types", "3GP 7Z AAC ACE AIF ARJ ASF ASPX AVI BIN GZ GZIP IMG ISO LZH M4A M4V MKV MOV MP3 MP4 MPA MPE MPEG MPG MSI MSU OGG OGV PDF RA RAR RM RMVB SEA SIT SITX TAR TAZ TGZ TS VOB WAV WMA WMV Z ZIP", type=str) or ""


def set_auto_file_types(types: str) -> None:
    _settings().setValue("auto_file_types", types or "")


def get_ignore_sites() -> str:
    return _settings().value("ignore_sites", "", type=str) or ""


def set_ignore_sites(sites: str) -> None:
    _settings().setValue("ignore_sites", sites or "")


def get_temp_directory() -> str:
    temp = _settings().value("temp_directory", "", type=str)
    return temp if temp and Path(temp).exists() else str(Path(os.environ.get("TEMP", "/tmp")))


def set_temp_directory(path: str) -> None:
    _settings().setValue("temp_directory", path or "")


_PROXY_MODES = ("none", "system", "manual")


def get_proxy_mode() -> str:
    v = (_settings().value("proxy_mode", "none", type=str) or "none").lower()
    return v if v in _PROXY_MODES else "none"


def set_proxy_mode(mode: str) -> None:
    m = (mode or "none").lower()
    _settings().setValue("proxy_mode", m if m in _PROXY_MODES else "none")


def get_proxy_host() -> str:
    return _settings().value("proxy_host", "", type=str) or ""


def set_proxy_host(host: str) -> None:
    _settings().setValue("proxy_host", host or "")


def get_proxy_port() -> int:
    try:
        v = int(_settings().value("proxy_port", 0))
    except (TypeError, ValueError):
        v = 0
    return max(0, min(65535, v))


def set_proxy_port(port: int) -> None:
    try:
        p = int(port)
    except (TypeError, ValueError):
        p = 0
    _settings().setValue("proxy_port", max(0, min(65535, p)))


def get_proxy_user() -> str:
    return _settings().value("proxy_user", "", type=str) or ""


def set_proxy_user(user: str) -> None:
    _settings().setValue("proxy_user", user or "")


def get_proxy_password() -> str:
    return _settings().value("proxy_password", "", type=str) or ""


def set_proxy_password(password: str) -> None:
    _settings().setValue("proxy_password", password or "")


def get_auto_categorize_enabled() -> bool:
    return bool(_settings().value("auto_categorize_enabled", True))


def set_auto_categorize_enabled(enabled: bool) -> None:
    _settings().setValue("auto_categorize_enabled", bool(enabled))


def get_category_directory(category: str) -> str:
    """Get directory for a specific file category."""
    base_dir = get_download_directory()
    category_dir = _settings().value(f"category_dir_{category}", "", type=str)
    if category_dir and Path(category_dir).exists():
        return category_dir
    return str(Path(base_dir) / category)


def set_category_directory(category: str, path: str) -> None:
    """Set directory for a specific file category."""
    _settings().setValue(f"category_dir_{category}", path or "")


def get_temp_cleanup_enabled() -> bool:
    return bool(_settings().value("temp_cleanup_enabled", True))


def set_temp_cleanup_enabled(enabled: bool) -> None:
    _settings().setValue("temp_cleanup_enabled", bool(enabled))


def get_temp_cleanup_hours() -> int:
    try:
        hours = int(_settings().value("temp_cleanup_hours", 24))
    except (TypeError, ValueError):
        hours = 24
    return max(1, min(168, hours))


def set_temp_cleanup_hours(hours: int) -> None:
    try:
        h = int(hours)
    except (TypeError, ValueError):
        h = 24
    _settings().setValue("temp_cleanup_hours", max(1, min(168, h)))


def get_remembered_directory(category: str) -> str:
    """Get the remembered directory for a specific category."""
    remembered_dir = _settings().value(f"remembered_dir_{category}", "", type=str)
    if remembered_dir and Path(remembered_dir).exists():
        return remembered_dir
    return ""


def set_remembered_directory(category: str, path: str) -> None:
    """Set the remembered directory for a specific category."""
    if path and Path(path).exists():
        _settings().setValue(f"remembered_dir_{category}", path)
    else:
        _settings().setValue(f"remembered_dir_{category}", "")


MAX_RECENT_FILES = 20


def get_recent_files() -> list[str]:
    """Get list of recent file paths."""
    s = _settings()
    recent = s.value("recent_files", [], type=list)
    if not isinstance(recent, list):
        return []
    existing_files = [f for f in recent if Path(f).exists()]
    if len(existing_files) != len(recent):
        set_recent_files(existing_files)
    return existing_files


def set_recent_files(files: list[str]) -> None:
    """Set list of recent file paths."""
    _settings().setValue("recent_files", files[:MAX_RECENT_FILES])


def add_recent_file(file_path: str) -> None:
    """Add a file to the recent files list."""
    if not file_path or not Path(file_path).exists():
        return
    
    recent = get_recent_files()
    if file_path in recent:
        recent.remove(file_path)
    recent.insert(0, file_path)
    recent = recent[:MAX_RECENT_FILES]
    set_recent_files(recent)


def clear_recent_files_settings() -> None:
    """Clear all recent files from settings."""
    set_recent_files([])


def get_sound_enabled(event: str) -> bool:
    """Check if sound is enabled for a specific event."""
    return bool(_settings().value(f"sound_enabled_{event}", True))


def set_sound_enabled(event: str, enabled: bool) -> None:
    """Enable or disable sound for a specific event."""
    _settings().setValue(f"sound_enabled_{event}", bool(enabled))


def get_sound_path(event: str) -> str:
    """Get the sound file path for a specific event."""
    return _settings().value(f"sound_path_{event}", "", type=str) or ""


def set_sound_path(event: str, path: str) -> None:
    """Set the sound file path for a specific event."""
    _settings().setValue(f"sound_path_{event}", path or "")


def get_master_volume() -> float:
    """Get master volume (0.0 to 1.0)."""
    try:
        vol = float(_settings().value("master_volume", 0.7))
    except (TypeError, ValueError):
        vol = 0.7
    return max(0.0, min(1.0, vol))


def set_master_volume(volume: float) -> None:
    """Set master volume (0.0 to 1.0)."""
    try:
        v = float(volume)
    except (TypeError, ValueError):
        v = 0.7
    _settings().setValue("master_volume", max(0.0, min(1.0, v)))


def get_sound_notifications_enabled() -> bool:
    """Check if sound notifications are globally enabled."""
    return bool(_settings().value("sound_notifications_enabled", True))


def set_sound_notifications_enabled(enabled: bool) -> None:
    """Enable or disable sound notifications globally."""
    _settings().setValue("sound_notifications_enabled", bool(enabled))
