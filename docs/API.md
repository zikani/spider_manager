# Spider Manager API Documentation

## Core Module APIs

### DownloadEngine

The `DownloadEngine` class is the main download engine supporting multiple download modes.

```python
class DownloadEngine:
    def __init__(
        self,
        segments: int = DEFAULT_SEGMENTS,
        speed_limiter: SpeedLimiter | None = None,
    ) -> None:
        """Initialize download engine.
        
        Args:
            segments: Number of parallel segments per download (1-32)
            speed_limiter: Optional speed limiter instance
        """
    
    async def probe(self, url: str, headers: dict | None = None) -> dict:
        """Probe URL to get file metadata.
        
        Returns:
            Dict with keys: size, filename, resumable, content_type, url, accepts_ranges
        """
    
    async def start(self, task: DownloadTask) -> None:
        """Start downloading a task.
        
        Args:
            task: DownloadTask to download
        """
    
    async def pause(self, task_id: str) -> None:
        """Pause a download by task ID."""
    
    async def cancel(self, task_id: str) -> None:
        """Cancel a download by task ID."""
    
    async def close(self) -> None:
        """Close the engine and cleanup resources."""
```

### DownloadTask

Dataclass representing a download job.

```python
@dataclass
class DownloadTask:
    id: str
    url: str
    filename: str
    save_path: str
    total_size: int = 0
    downloaded: int = 0
    state: str = DownloadState.QUEUED
    category: str = "Other"
    download_mode: str = "direct"
    segments: list[DownloadSegment] = field(default_factory=list)
    stream_segments: list[StreamSegment] = field(default_factory=list)
    error: str = ""
    retry_count: int = 0
    started_at: float | None = None
    completed_at: float | None = None
    progress_callback: Callable | None = None
    state_callback: Callable | None = None
    
    @property
    def progress(self) -> float:
        """Download progress percentage (0-100)."""
    
    @property
    def speed(self) -> float:
        """Current download speed in bytes/sec."""
    
    @property
    def eta(self) -> float:
        """Estimated time remaining in seconds."""
    
    @property
    def stats(self) -> dict:
        """Snapshot dict for UI updates."""
```

### QueueManager

Manages the global download queue with priority scheduling.

```python
class QueueManager(QObject):
    download_completed = pyqtSignal(str)  # task_id
    download_failed = pyqtSignal(str)     # task_id
    queue_finished = pyqtSignal()         # all downloads complete
    
    def __init__(
        self,
        engine: DownloadEngine,
        max_concurrent: int = DEFAULT_CONCURRENT,
        scheduler_allows_dispatch: Callable[[], bool] | None = None,
    ) -> None:
        """Initialize queue manager.
        
        Args:
            engine: DownloadEngine instance
            max_concurrent: Maximum concurrent downloads
            scheduler_allows_dispatch: Optional callback for scheduler
        """
    
    async def add(self, task: DownloadTask) -> None:
        """Add a task to the queue."""
    
    async def remove(self, task_id: str) -> None:
        """Remove a task from the queue."""
    
    async def pause(self, task_id: str) -> None:
        """Pause a download."""
    
    async def resume(self, task_id: str) -> None:
        """Resume a paused download."""
    
    async def cancel(self, task_id: str) -> None:
        """Cancel a download."""
    
    def create_task(
        self,
        url: str,
        filename: str,
        save_path: str,
        category: str = "Other",
    ) -> DownloadTask:
        """Create a new DownloadTask."""
    
    def get_task(self, task_id: str) -> DownloadTask | None:
        """Get task by ID."""
    
    def get_by_category(self, category: str) -> list[DownloadTask]:
        """Get all tasks in a category."""
    
    def get_category_counts(self) -> dict[str, int]:
        """Get count of tasks per category."""
    
    def save_queue(self) -> None:
        """Save queue to disk."""
    
    async def clear_queue(self) -> None:
        """Clear all tasks from queue."""
    
    async def clear_completed(self) -> None:
        """Clear completed tasks."""
```

### SpeedLimiter

Global bandwidth throttling using token bucket algorithm.

```python
class SpeedLimiter:
    def __init__(self, limit_bps: int = 0) -> None:
        """Initialize speed limiter.
        
        Args:
            limit_bps: Speed limit in bytes/sec (0 = unlimited)
        """
    
    def set_limit_bps(self, limit_bps: int) -> None:
        """Update speed limit."""
    
    async def consume(self, bytes_count: int) -> None:
        """Consume bytes, sleeping if necessary to respect limit."""
```

## Plugin System APIs

### SpiderPlugin

Base class for all plugins.

```python
class SpiderPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Plugin priority (higher = checked first)."""
    
    @property
    @abstractmethod
    def capabilities(self) -> PluginCapability:
        """Plugin capability flags."""
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if plugin can handle this URL."""
    
    @abstractmethod
    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        """Process URL and return PluginResult."""
```

### PluginResult

Result from plugin processing.

```python
@dataclass
class PluginResult:
    url: str
    filename: str
    download_mode: DownloadMode
    total_size: int = 0
    content_type: str = ""
    stream_segments: list[StreamSegment] = field(default_factory=list)
    stream_manifest_url: str = ""
    stream_type: str = ""
    stream_duration_sec: float = 0.0
    thumbnail_url: str = ""
    chapters: list[dict] = field(default_factory=list)
    subtitles: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

### PluginContext

Context passed to plugin process method.

```python
@dataclass
class PluginContext:
    save_path: str
    preferred_quality: str = "720p"
    preferred_format: str = "mp4"
    download_subtitles: bool = False
    subtitle_languages: list[str] = field(default_factory=list)
    cookies: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    proxy: str = ""
```

### PluginCapability

Capability flags for plugins.

```python
class PluginCapability:
    NONE = 0
    URL_HANDLING = 1
    STREAM_EXTRACTION = 2
    METADATA_EXTRACTION = 4
```

### DownloadMode

Download mode enumeration.

```python
class DownloadMode:
    DIRECT = "direct"
    STREAM_HLS = "stream_hls"
    STREAM_DASH = "stream_dash"
    YTDLP = "ytdlp"
    BLOB = "blob"
```

## Configuration APIs

### Settings Module

User preferences via QSettings.

```python
def get_download_directory() -> str:
    """Get default download directory."""

def set_download_directory(path: str) -> None:
    """Set default download directory."""

def get_segment_count() -> int:
    """Get segment count (1-32)."""

def set_segment_count(n: int) -> None:
    """Set segment count."""

def get_max_concurrent() -> int:
    """Get max concurrent downloads (1-10)."""

def set_max_concurrent(n: int) -> None:
    """Set max concurrent downloads."""

def get_speed_limit_kb() -> int:
    """Get speed limit in KB/s (0 = unlimited)."""

def set_speed_limit_kb(kb: int) -> None:
    """Set speed limit in KB/s."""

def get_scheduler_enabled() -> bool:
    """Check if scheduler is enabled."""

def set_scheduler_enabled(enabled: bool) -> None:
    """Enable/disable scheduler."""

def get_scheduler_start() -> str:
    """Get scheduler start time (HH:MM)."""

def set_scheduler_start(value: str) -> None:
    """Set scheduler start time."""

def get_scheduler_end() -> str:
    """Get scheduler end time (HH:MM)."""

def set_scheduler_end(value: str) -> None:
    """Set scheduler end time."""

def get_ui_theme() -> str:
    """Get UI theme ('dark' or 'light')."""

def set_ui_theme(theme: str) -> None:
    """Set UI theme."""

def get_sound_notifications_enabled() -> bool:
    """Check if sound notifications are enabled."""

def set_sound_notifications_enabled(enabled: bool) -> None:
    """Enable/disable sound notifications."""
```

## Utility APIs

### File Utils

```python
def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe filesystem usage."""

def unique_path(directory: Path, filename: str) -> str:
    """Get unique path, appending counter if needed."""

def get_free_space(path: Path) -> int:
    """Get free disk space in bytes."""

def ensure_directory(path: Path) -> None:
    """Ensure directory exists, creating if needed."""

def format_size(bytes: int) -> str:
    """Format bytes to human-readable string."""
```

### Network Utils

```python
def build_proxy_url(
    host: str,
    port: int,
    username: str = "",
    password: str = "",
) -> str | None:
    """Build proxy URL from components."""

def system_proxy() -> str | None:
    """Get system proxy from environment variables."""

def resolve_ip(host: str) -> str | None:
    """Resolve hostname to IP address."""

def is_reachable(host: str, port: int, timeout: float = 5.0) -> bool:
    """Check if host:port is reachable."""
```

### URL Parser

```python
def is_valid_url(url: str) -> bool:
    """Check if URL is valid and supported."""

def extract_filename(url: str, headers: dict | None = None) -> str:
    """Extract filename from URL or headers."""

def safe_filename_from_url(url: str, headers: dict | None = None) -> str:
    """Extract and sanitize filename from URL."""
```

## Constants

### DownloadState

```python
class DownloadState:
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    MERGING = "merging"
    VERIFYING = "verifying"
```

### Categories

```python
CATEGORIES = {
    "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg"],
    "Audio": [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus", ".wma"],
    "Image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff"],
    "Document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".epub"],
    "Archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Program": [".exe", ".msi", ".deb", ".rpm", ".dmg", ".apk", ".appimage"],
    "Other": [],
}
```

### Default Values

```python
DEFAULT_SEGMENTS = 8
MAX_SEGMENTS = 32
DEFAULT_CONCURRENT = 3
MAX_CONCURRENT_DOWNLOADS = 5
CONNECTION_TIMEOUT = 30
READ_TIMEOUT = 60
DEFAULT_RETRY_COUNT = 5
RETRY_DELAY = 3
```
