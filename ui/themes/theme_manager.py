"""Apply dark / light QSS + frameless window chrome."""

from config import settings as app_settings
from ui.themes.dark_theme import DARK_QSS
from ui.themes.light_theme import LIGHT_QSS

FRAME_DARK = """
QMainWindow { background: transparent; }
#appContainer { background: #0d1117; border-radius: 10px; border: 1px solid #30363d; }
#titleBar { background: #161b22; border-bottom: 1px solid #30363d;
  border-top-left-radius: 10px; border-top-right-radius: 10px; }
#titleBarTitle { color: #8b949e; font-size: 12px; font-weight: 500; letter-spacing: 0.5px; }
"""

FRAME_LIGHT = """
QMainWindow { background: transparent; }
#appContainer { background: #ffffff; border-radius: 10px; border: 1px solid #d0d7de; }
#titleBar { background: #f6f8fa; border-bottom: 1px solid #d0d7de;
  border-top-left-radius: 10px; border-top-right-radius: 10px; }
#titleBarTitle { color: #59636e; font-size: 12px; font-weight: 500; letter-spacing: 0.5px; }
"""


def current_stylesheet() -> str:
    theme = app_settings.get_ui_theme()
    if theme == "light":
        return LIGHT_QSS + FRAME_LIGHT
    return DARK_QSS + FRAME_DARK


def apply_theme_to_window(window) -> None:
    window.setStyleSheet(current_stylesheet())
