"""Auto-generated icon constants for Spider Download Manager."""
from enum import Enum

class Icons(str, Enum):
    """Paths to SVG icon files (relative to icons/ directory)."""
    DOWNLOAD = "transfer/download.svg"  # Start or add a download
    UPLOAD = "transfer/upload.svg"  # Upload / seeding
    DOWNLOAD_QUEUE = "transfer/download_queue.svg"  # Queue / list of downloads
    DOWNLOAD_ALL = "transfer/download_all.svg"  # Download all / batch download
    SPEED_LIMIT = "transfer/speed_limit.svg"  # Speed / bandwidth limit
    BANDWIDTH = "transfer/bandwidth.svg"  # Bandwidth usage / network
    TRANSFER_ARROWS = "transfer/transfer_arrows.svg"  # Two-way transfer / sync
    PLAY = "controls/play.svg"  # Resume / start
    PAUSE = "controls/pause.svg"  # Pause download
    STOP = "controls/stop.svg"  # Stop / cancel
    RESUME = "controls/resume.svg"  # Resume from paused state
    RESTART = "controls/restart.svg"  # Restart download
    SKIP = "controls/skip.svg"  # Skip / next item
    FILE = "files/file.svg"  # Generic file
    FILE_VIDEO = "files/file_video.svg"  # Video file
    FILE_AUDIO = "files/file_audio.svg"  # Audio file
    FILE_IMAGE = "files/file_image.svg"  # Image file
    FILE_ARCHIVE = "files/file_archive.svg"  # Compressed archive (zip, rar, torrent)
    FOLDER = "files/folder.svg"  # Folder / save location
    FOLDER_OPEN = "files/folder_open.svg"  # Open download folder
    SAVE_AS = "files/save_as.svg"  # Save / rename file
    MOVE_FILE = "files/move_file.svg"  # Move file to folder
    LINK = "network/link.svg"  # URL / hyperlink
    LINK_ADD = "network/link_add.svg"  # Add URL / paste link
    GLOBE = "network/globe.svg"  # Browser / web source
    SERVER = "network/server.svg"  # Server / FTP / proxy
    WIFI = "network/wifi.svg"  # WiFi / wireless connection
    PROXY = "network/proxy.svg"  # Proxy / VPN settings
    MAGNET = "network/magnet.svg"  # Magnet link / torrent
    TORRENT = "network/torrent.svg"  # BitTorrent / P2P
    RSS = "network/rss.svg"  # RSS / media feed
    STATUS_COMPLETE = "status/status_complete.svg"  # Download complete
    STATUS_ERROR = "status/status_error.svg"  # Download failed / error
    STATUS_PAUSED = "status/status_paused.svg"  # Download paused
    STATUS_SEEDING = "status/status_seeding.svg"  # Seeding / uploading
    STATUS_QUEUED = "status/status_queued.svg"  # Queued / waiting
    NOTIFICATION = "status/notification.svg"  # Notifications / alerts
    WARNING = "status/warning.svg"  # Warning / caution
    INFO = "status/info.svg"  # Information
    SETTINGS = "app/settings.svg"  # Settings / preferences
    ADD = "app/add.svg"  # Add new download
    DELETE = "app/delete.svg"  # Delete / remove
    SEARCH = "app/search.svg"  # Search downloads
    FILTER = "app/filter.svg"  # Filter list
    SORT = "app/sort.svg"  # Sort / order list
    REFRESH = "app/refresh.svg"  # Refresh / retry
    COPY = "app/copy.svg"  # Copy URL / text
    PASTE = "app/paste.svg"  # Paste URL from clipboard
    CLEAR_ALL = "app/clear_all.svg"  # Clear all / remove all
    SELECT_ALL = "app/select_all.svg"  # Select all items
    CHECKBOX_EMPTY = "app/checkbox_empty.svg"  # Unchecked checkbox
    CHECKBOX_CHECKED = "app/checkbox_checked.svg"  # Checked checkbox
    HOME = "nav/home.svg"  # Dashboard / home
    HISTORY = "nav/history.svg"  # Download history
    SCHEDULER = "nav/scheduler.svg"  # Scheduler / timed downloads
    CATEGORIES = "nav/categories.svg"  # Categories / file types
    STATS = "nav/stats.svg"  # Statistics / graphs
    EXTENSIONS = "nav/extensions.svg"  # Extensions / plugins
    VIEW_LIST = "view/view_list.svg"  # List view
    VIEW_GRID = "view/view_grid.svg"  # Grid view
    COLUMNS = "view/columns.svg"  # Column layout toggle
    SIDEBAR_TOGGLE = "view/sidebar_toggle.svg"  # Toggle sidebar
    FULLSCREEN = "view/fullscreen.svg"  # Fullscreen / maximize
    MINIMIZE = "view/minimize.svg"  # Minimize window
    TRAY = "view/tray.svg"  # System tray / minimize to tray
    LOCK = "security/lock.svg"  # Lock / secured
    UNLOCK = "security/unlock.svg"  # Unlock / unsecured
    KEY = "security/key.svg"  # Authentication key
    SHIELD = "security/shield.svg"  # Security / virus check
    PREVIEW = "media/preview.svg"  # Preview / open file
    THUMBNAIL = "media/thumbnail.svg"  # Thumbnail / media preview
    MEDIA_VIDEO = "media/media_video.svg"  # Video player / playback
    OPTIONS_DOTS = "misc/options_dots.svg"  # More options (vertical)
    OPTIONS_DOTS_H = "misc/options_dots_h.svg"  # More options (horizontal)
    TAG = "misc/tag.svg"  # Tag / label
    NOTES = "misc/notes.svg"  # Notes / comments
    SHARE = "misc/share.svg"  # Share / export link
    IMPORT = "misc/import.svg"  # Import config / batch
    EXPORT = "misc/export.svg"  # Export config / list
    PLUGIN = "misc/plugin.svg"  # Plugin / integration
    SPIDER_LOGO = "brand/spider_logo.svg"  # Spider app logo — web with spider
    SPIDER_WEB = "brand/spider_web.svg"  # Spider web — loading / processing

    @property
    def resource_path(self) -> str:
        """Returns Qt resource path: :/icons/<name>.svg"""
        return f":/icons/{self.name.lower().replace(chr(95), chr(95))}.svg"