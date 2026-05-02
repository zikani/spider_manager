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


# Global speed limit (kilobytes/sec, 0 = unlimited)
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
    v = _settings().value("scheduler_start", "09:00", type=str)
    return v if v else "09:00"


def set_scheduler_start(value: str) -> None:
    _settings().setValue("scheduler_start", value or "09:00")


def get_scheduler_end() -> str:
    v = _settings().value("scheduler_end", "21:00", type=str)
    return v if v else "21:00"


def set_scheduler_end(value: str) -> None:
    _settings().setValue("scheduler_end", value or "21:00")


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


# New settings for IDM-like features
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
