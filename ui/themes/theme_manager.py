"""Apply dark / light QSS + frameless window chrome."""

from config import settings as app_settings
from ui.themes.dark_theme import DARK_QSS
from ui.themes.light_theme import LIGHT_QSS

FRAME_DARK = """
QMainWindow { background: transparent; }
  border-top-left-radius: 10px; border-top-right-radius: 10px; }
"""

FRAME_LIGHT = """
QMainWindow { background: transparent; }
  border-top-left-radius: 10px; border-top-right-radius: 10px; }
"""


def current_stylesheet() -> str:
    theme = app_settings.get_ui_theme()
    if theme == "light":
        return LIGHT_QSS + FRAME_LIGHT
    return DARK_QSS + FRAME_DARK


def apply_theme_to_window(window) -> None:
    window.setStyleSheet(current_stylesheet())
