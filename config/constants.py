"""
Spider Manager - Application Constants
"""

APP_NAME = "Spider Manager"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Spider Manager Team"
APP_DESCRIPTION = "A professional download manager built with Python and PyQt6"
APP_URL = "https://github.com/yourusername/spider-manager"

# Download Engine
DEFAULT_SEGMENTS = 8          # Parallel segments per download
MAX_SEGMENTS = 32
MIN_SEGMENT_SIZE = 1024 * 512  # 512 KB minimum per segment
DEFAULT_RETRY_COUNT = 5
RETRY_DELAY = 3                # seconds
CONNECTION_TIMEOUT = 30        # seconds
READ_TIMEOUT = 60

# Queue
MAX_CONCURRENT_DOWNLOADS = 5
DEFAULT_CONCURRENT = 3

# Speed
SPEED_UPDATE_INTERVAL = 500    # ms
GRAPH_HISTORY_POINTS = 60

# UI
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600
SIDEBAR_WIDTH = 200
TOOLBAR_HEIGHT = 48
STATUSBAR_HEIGHT = 28

# File categories
CATEGORIES = {
    "Video":    [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg"],
    "Audio":    [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus", ".wma"],
    "Image":    [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff"],
    "Document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".epub"],
    "Archive":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Program":  [".exe", ".msi", ".deb", ".rpm", ".dmg", ".apk", ".appimage"],
    "Other":    [],
}


def category_for_filename(filename: str) -> str:
    """Map file extension to category name."""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    for cat, exts in CATEGORIES.items():
        if cat == "Other":
            continue
        if ext in exts:
            return cat
    return "Other"

# Download states
class DownloadState:
    QUEUED      = "queued"
    DOWNLOADING = "downloading"
    PAUSED      = "paused"
    COMPLETED   = "completed"
    ERROR       = "error"
    CANCELLED   = "cancelled"
    MERGING     = "merging"
    VERIFYING   = "verifying"

# Colors (Dark Theme)
COLOR_BG_PRIMARY    = "#0d1117"
COLOR_BG_SECONDARY  = "#161b22"
COLOR_BG_TERTIARY   = "#21262d"
COLOR_ACCENT_BLUE   = "#58a6ff"
COLOR_ACCENT_GREEN  = "#3fb950"
COLOR_ACCENT_ORANGE = "#f78166"
COLOR_ACCENT_YELLOW = "#d29922"
COLOR_TEXT_PRIMARY  = "#e6edf3"
COLOR_TEXT_SECONDARY= "#8b949e"
COLOR_BORDER        = "#30363d"
COLOR_HOVER         = "#1f2937"
