"""
Spider Manager — Plugin Base  v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v0.0.3 improvements over v0.0.2:
  • StreamingCapability flag — proper STREAMING / HLS / DASH / DIRECT distinction
  • DownloadMode enum — DIRECT | STREAM_HLS | STREAM_DASH | YTDLP | BROWSER
  • PluginResult.stream_manifest_url — separate from direct download url
  • PluginResult.download_mode — tells the engine which strategy to use
  • PluginResult.segment_urls — pre-resolved HLS/DASH segment list (optional)
  • MediaFormat.is_hls / is_dash / is_fragmented flags
  • PluginContext.max_concurrent_fragments — concurrency hint for fragment DL
  • PluginRegistry.process_streaming() — dedicated streaming dispatch
  • Better error hierarchy: PluginStreamError, PluginTimeoutError
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Flag, auto, Enum
from typing import Any, Optional

from utils.logger import get_logger

log = get_logger(__name__)



class PluginCapability(Flag):
    """Bit-flags advertising what a plugin can do."""
    NONE                 = 0
    RESUMABLE            = auto()
    PLAYLIST             = auto()
    AUTH_REQUIRED        = auto()
    STREAMING            = auto()
    STREAMING_HLS        = auto()
    STREAMING_DASH       = auto()
    STREAMING_LIVE       = auto()
    METADATA_ONLY        = auto()
    CHECKSUM             = auto()
    SUBTITLE             = auto()
    THUMBNAIL            = auto()
    DIRECT_DOWNLOAD      = auto()
    FRAGMENT_DOWNLOAD    = auto()



class PluginError(Exception):
    """Base exception for all plugin failures."""

class PluginNotApplicable(PluginError):
    """Raised when no plugin can handle a URL."""

class PluginDependencyMissing(PluginError):
    """Raised when a required third-party package is absent."""
    def __init__(self, package: str):
        self.package = package
        super().__init__(
            f"Required package '{package}' is not installed. "
            f"Run: pip install {package}"
        )

class PluginAuthError(PluginError):
    """Raised when authentication credentials are missing or rejected."""

class PluginNetworkError(PluginError):
    """Raised on network-level failures inside the plugin."""

class PluginStreamError(PluginError):
    """Raised when a streaming manifest cannot be parsed or fetched."""

class PluginTimeoutError(PluginError):
    """Raised when a plugin operation times out."""

class PluginGeoBlockedError(PluginError):
    """Raised when content is geo-restricted and bypass failed."""



class DownloadMode(Enum):
    """
    Tells the download engine which strategy to use.
    Attached to every PluginResult so the engine doesn't have to guess.
    """
    DIRECT      = "direct"
    STREAM_HLS  = "stream_hls"
    STREAM_DASH = "stream_dash"
    YTDLP       = "ytdlp"
    BROWSER     = "browser"
    BLOB        = "blob"



@dataclass
class MediaFormat:
    """
    Describes one available format variant for a media URL.
    e.g. '1080p MP4 (H.264+AAC, 2.1 GB)'
    """
    format_id: str
    label: str
    ext: str
    width: int = 0
    height: int = 0
    fps: float = 0.0
    audio_bitrate: int = 0
    video_bitrate: int = 0
    filesize: int = 0
    is_audio_only: bool = False
    is_video_only: bool = False
    vcodec: str = ""
    acodec: str = ""
    note: str = ""

    is_hls: bool = False
    is_dash: bool = False
    is_fragmented: bool = False
    manifest_url: str = ""
    segment_count: int = 0
    bandwidth_bps: int = 0

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "audio-only" if self.is_audio_only else "unknown"

    @property
    def is_streaming(self) -> bool:
        return self.is_hls or self.is_dash or self.is_fragmented

    def __str__(self) -> str:
        parts = [self.label]
        if self.resolution != "unknown":
            parts.append(f"({self.resolution})")
        if self.filesize:
            from utils.file_utils import human_size
            parts.append(human_size(self.filesize))
        return " ".join(parts)



@dataclass
class StreamSegment:
    """Represents a single fragment / segment in an HLS or DASH stream."""
    url: str
    index: int = 0
    duration_sec: float = 0.0
    byterange: Optional[tuple[int, int]] = None
    encryption_key_url: str = ""
    encryption_iv: str = ""
    is_init_segment: bool = False



@dataclass
class PluginResult:
    """
    Typed, validated descriptor returned from SpiderPlugin.process().
    Everything the download engine needs is here.
    """
    url:      str
    filename: str

    download_mode: DownloadMode = DownloadMode.DIRECT

    size: int = 0
    expected_checksum: str = ""

    headers: dict = field(default_factory=dict)
    referrer: str = ""
    cookies: dict = field(default_factory=dict)

    stream_manifest_url: str = ""
    stream_segments: list[StreamSegment] = field(default_factory=list)
    stream_duration_sec: float = 0.0
    is_live: bool = False
    stream_type: str = ""

    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    duration_sec: float = 0.0
    uploader: str = ""
    upload_date: str = ""
    view_count: int = 0
    like_count: int = 0

    chosen_format: Optional[MediaFormat] = None
    all_formats: list[MediaFormat] = field(default_factory=list)

    is_playlist: bool = False
    playlist_title: str = ""
    playlist_items: list["PluginResult"] = field(default_factory=list)

    subtitles: dict[str, str] = field(default_factory=dict)

    plugin_name: str = ""
    extracted_at: float = field(default_factory=time.time)


    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("PluginResult.url must not be empty")
        if not self.filename:
            raise ValueError("PluginResult.filename must not be empty")
        if self.expected_checksum and ":" not in self.expected_checksum:
            raise ValueError(
                "expected_checksum must be 'algo:hexdigest', e.g. 'sha256:abcdef…'"
            )
        if self.download_mode == DownloadMode.DIRECT:
            self.download_mode = self._infer_download_mode()

    def _infer_download_mode(self) -> DownloadMode:
        """Infer download strategy from URL and stream_type."""
        url_lower = self.url.lower()
        st = self.stream_type.lower()
        if self.is_live:
            return DownloadMode.STREAM_HLS
        if st == "hls" or ".m3u8" in url_lower or ".m3u" in url_lower:
            return DownloadMode.STREAM_HLS
        if st == "dash" or ".mpd" in url_lower:
            return DownloadMode.STREAM_DASH
        if self.url.startswith("blob:"):
            return DownloadMode.BLOB
        return DownloadMode.DIRECT


    @property
    def is_streaming(self) -> bool:
        return self.download_mode in (
            DownloadMode.STREAM_HLS, DownloadMode.STREAM_DASH, DownloadMode.BLOB
        )


    def to_task_kwargs(self) -> dict:
        """
        Return a dict of kwargs ready to pass to QueueManager.create_task().
        Merges cookies into the headers dict automatically.
        """
        from utils.mime_detector import category_from_filename
        merged_headers = dict(self.headers)
        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            merged_headers["Cookie"] = cookie_str
        if self.referrer:
            merged_headers.setdefault("Referer", self.referrer)

        kwargs = {
            "url":               self.url,
            "filename":          self.filename,
            "category":          category_from_filename(self.filename),
            "referrer":          self.referrer,
            "headers":           merged_headers,
            "expected_checksum": self.expected_checksum,
            "download_mode":     self.download_mode.value,
        }

        if self.is_streaming:
            kwargs.update({
                "stream_manifest_url": self.stream_manifest_url or self.url,
                "stream_type":         self.stream_type,
                "stream_duration_sec": self.stream_duration_sec,
                "is_live":             self.is_live,
            })
            if self.stream_segments:
                kwargs["stream_segments"] = [
                    {
                        "url":       s.url,
                        "index":     s.index,
                        "duration":  s.duration_sec,
                        "byterange": s.byterange,
                        "key_url":   s.encryption_key_url,
                        "iv":        s.encryption_iv,
                        "is_init":   s.is_init_segment,
                    }
                    for s in self.stream_segments
                ]

        return kwargs

    def __repr__(self) -> str:
        fmt = f" format={self.chosen_format.label!r}" if self.chosen_format else ""
        size_s = f" size={self.size:,}B" if self.size else ""
        mode = f" mode={self.download_mode.value}"
        return f"<PluginResult plugin={self.plugin_name!r} file={self.filename!r}{fmt}{size_s}{mode}>"



@dataclass
class PluginContext:
    """
    Snapshot of runtime preferences passed to every plugin invocation.
    Built automatically from the global Settings singleton via from_settings().
    """
    proxy:                     Optional[str] = None
    user_agent:                str           = "Spider-Manager/1.0"
    preferred_ext:             str           = "mp4"
    preferred_quality:         str           = "best"
    embed_subs:                bool          = False
    write_thumbnail:           bool          = False
    cookies_file:              Optional[str] = None
    output_dir:                str           = ""

    max_concurrent_fragments:  int           = 4
    stream_segment_timeout:    float         = 30.0
    prefer_native_hls:         bool          = False
    hls_use_mpegts:            bool          = True
    dash_prefer_audio_lang:    str           = "en"
    ffmpeg_path:               Optional[str] = None
    stream_retry_count:        int           = 3

    extra: dict = field(default_factory=dict)

    @classmethod
    def from_settings(cls) -> "PluginContext":
        """Build a PluginContext from the global Settings singleton."""
        from config.settings import get_settings
        from utils.network_utils import current_proxy, default_user_agent
        s = get_settings()
        return cls(
            proxy                    = current_proxy(),
            user_agent               = default_user_agent(),
            preferred_ext            = s.get("preferred_video_ext", "mp4"),
            preferred_quality        = s.get("preferred_quality", "best"),
            embed_subs               = s.get("embed_subtitles", False),
            write_thumbnail          = s.get("write_thumbnail", False),
            cookies_file             = s.get("cookies_file") or None,
            output_dir               = s.get("download_path", ""),
            max_concurrent_fragments = s.get("max_concurrent_fragments", 4),
            stream_segment_timeout   = s.get("stream_segment_timeout", 30.0),
            prefer_native_hls        = s.get("prefer_native_hls", False),
            hls_use_mpegts           = s.get("hls_use_mpegts", True),
            dash_prefer_audio_lang   = s.get("dash_prefer_audio_lang", "en"),
            ffmpeg_path              = s.get("ffmpeg_path") or None,
            stream_retry_count       = s.get("stream_retry_count", 3),
        )



class SpiderPlugin(ABC):
    """
    Abstract base every Spider Manager plugin must subclass.

    Minimal implementation: name, description, can_handle(), process().
    Everything else has a sensible default.
    """


    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier, e.g. 'yt-dlp'."""

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line human-readable description."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return ""


    @property
    def capabilities(self) -> PluginCapability:
        """Override to advertise supported features."""
        return PluginCapability.NONE

    @property
    def priority(self) -> int:
        """
        Plugins are tried in descending priority order.
        Range 0–100. Default 50.  Browser extension uses 10 (fallback).
        yt-dlp uses 90 (trusted extractor for media).
        """
        return 50


    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Fast check (no network) — return True if this plugin handles `url`.
        """


    @abstractmethod
    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        """
        Resolve `url` into a direct download descriptor.

        Args:
            url:  Original URL from the user.
            ctx:  Runtime context.

        Returns:
            PluginResult  — validated and ready to hand to the engine.

        Raises:
            PluginError subclass on failure.
        """


    async def resolve_stream_segments(
        self, manifest_url: str, ctx: PluginContext
    ) -> list[StreamSegment]:
        """
        Parse a streaming manifest and return ordered segment list.
        Override in streaming-capable plugins. Default returns empty list
        (the engine will handle it via ffmpeg or yt-dlp).
        """
        return []

    async def get_best_stream_variant(
        self, manifest_url: str, ctx: PluginContext
    ) -> Optional[str]:
        """
        For HLS/DASH master playlists, return the best variant URL
        based on ctx.preferred_quality. Returns None to let the engine decide.
        """
        return None


    async def preferred_formats(
        self, url: str, ctx: PluginContext
    ) -> list[MediaFormat]:
        """Return available formats without downloading. Override in media plugins."""
        return []

    def select_format(
        self, formats: list[MediaFormat], ctx: PluginContext
    ) -> Optional[MediaFormat]:
        """
        Pick the best format from `formats` based on ctx.preferred_quality.

        Built-in strategy:
          "best"   → highest height then highest audio bitrate
          "worst"  → lowest
          "audio"  → audio-only, highest bitrate
          "<N>p"   → closest to N vertical pixels (e.g. "720p")
        """
        if not formats:
            return None

        q = ctx.preferred_quality.lower()

        if q == "audio":
            audio = [f for f in formats if f.is_audio_only]
            pool = audio if audio else formats
            return max(pool, key=lambda f: f.audio_bitrate)

        target_h: Optional[int] = None
        if q.endswith("p") and q[:-1].isdigit():
            target_h = int(q[:-1])

        video = [f for f in formats if not f.is_audio_only] or formats

        if target_h is not None:
            return min(video, key=lambda f: abs(f.height - target_h))
        if q == "worst":
            return min(video, key=lambda f: (f.height, f.audio_bitrate))
        return max(video, key=lambda f: (f.height, f.audio_bitrate))


    def on_start(self, url: str, ctx: PluginContext) -> None:
        """Called just before process(). E.g. refresh OAuth token."""

    def on_success(self, url: str, result: PluginResult) -> None:
        """Called after process() succeeds."""

    def on_failure(self, url: str, error: Exception) -> None:
        """Called when process() raises."""


    async def run(
        self, url: str, ctx: Optional[PluginContext] = None
    ) -> PluginResult:
        """
        Fire lifecycle hooks, call process(), stamp result, log timing.
        Prefer calling this over process() directly.
        """
        ctx = ctx or PluginContext.from_settings()
        self.on_start(url, ctx)
        t0 = time.monotonic()
        try:
            result = await self.process(url, ctx)
            result.plugin_name = self.name
            elapsed = time.monotonic() - t0
            log.info("[%s] Processed in %.2fs → %s", self.name, elapsed, result.filename)
            self.on_success(url, result)
            return result
        except PluginError:
            raise
        except Exception as exc:
            self.on_failure(url, exc)
            raise PluginError(f"[{self.name}] Unexpected error: {exc}") from exc

    def __repr__(self) -> str:
        caps = str(self.capabilities).replace("PluginCapability.", "")
        return (
            f"<{self.__class__.__name__} name={self.name!r} "
            f"priority={self.priority} caps={caps}>"
        )



class PluginRegistry:
    """
    Global singleton managing all registered SpiderPlugin instances.

        registry = PluginRegistry.instance()
        registry.load_defaults()
        result = await registry.process(url)
    """

    _singleton: Optional["PluginRegistry"] = None

    def __init__(self) -> None:
        self._plugins: list[SpiderPlugin] = []

    @classmethod
    def instance(cls) -> "PluginRegistry":
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton


    def register(self, plugin: SpiderPlugin) -> None:
        """Register. Duplicate names are silently replaced."""
        self._plugins = [p for p in self._plugins if p.name != plugin.name]
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority, reverse=True)
        log.info("Plugin registered: %r", plugin)

    def unregister(self, name: str) -> bool:
        before = len(self._plugins)
        self._plugins = [p for p in self._plugins if p.name != name]
        return len(self._plugins) < before

    def get(self, name: str) -> Optional[SpiderPlugin]:
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    @property
    def all(self) -> list[SpiderPlugin]:
        return list(self._plugins)


    def find(self, url: str) -> Optional[SpiderPlugin]:
        """Highest-priority plugin that can_handle(url), or None."""
        for plugin in self._plugins:
            try:
                if plugin.can_handle(url):
                    log.debug("Plugin '%s' matched: %s", plugin.name, url)
                    return plugin
            except Exception as exc:
                log.warning("Plugin '%s'.can_handle() raised: %s", plugin.name, exc)
        return None

    def find_all(self, url: str) -> list[SpiderPlugin]:
        """All plugins that can_handle(url), in priority order."""
        out = []
        for plugin in self._plugins:
            try:
                if plugin.can_handle(url):
                    out.append(plugin)
            except Exception:
                pass
        return out

    def find_for_streaming(self, url: str) -> list[SpiderPlugin]:
        """
        Returns plugins capable of streaming that can handle this URL.
        Streaming-capable plugins are prioritised first.
        """
        streaming_caps = (
            PluginCapability.STREAMING
            | PluginCapability.STREAMING_HLS
            | PluginCapability.STREAMING_DASH
            | PluginCapability.FRAGMENT_DOWNLOAD
        )
        candidates = self.find_all(url)
        streaming  = [p for p in candidates if p.capabilities & streaming_caps]
        rest       = [p for p in candidates if p not in streaming]
        return streaming + rest

    async def process(
        self, url: str, ctx: Optional[PluginContext] = None
    ) -> PluginResult:
        """
        Dispatch to the best plugin. Falls through to the next on failure.
        Raises PluginNotApplicable if nothing matches.
        """
        candidates = self.find_all(url)
        if not candidates:
            raise PluginNotApplicable(f"No plugin can handle: {url}")

        last_err: Optional[Exception] = None
        for plugin in candidates:
            try:
                return await plugin.run(url, ctx)
            except PluginError as exc:
                log.warning(
                    "Plugin '%s' failed for %s: %s — trying next",
                    plugin.name, url, exc,
                )
                last_err = exc

        raise last_err or PluginNotApplicable(url)

    async def process_streaming(
        self, url: str, ctx: Optional[PluginContext] = None
    ) -> PluginResult:
        """
        Like process() but prefers streaming-capable plugins.
        Used when the caller already knows the URL is a stream manifest.
        """
        candidates = self.find_for_streaming(url)
        if not candidates:
            raise PluginNotApplicable(f"No streaming plugin can handle: {url}")

        last_err: Optional[Exception] = None
        for plugin in candidates:
            try:
                result = await plugin.run(url, ctx)
                if result.download_mode == DownloadMode.DIRECT:
                    url_lower = url.lower()
                    if ".m3u8" in url_lower or ".m3u" in url_lower:
                        result.download_mode = DownloadMode.STREAM_HLS
                    elif ".mpd" in url_lower:
                        result.download_mode = DownloadMode.STREAM_DASH
                return result
            except PluginError as exc:
                log.warning(
                    "Streaming plugin '%s' failed for %s: %s — trying next",
                    plugin.name, url, exc,
                )
                last_err = exc

        raise last_err or PluginNotApplicable(url)


    def load_defaults(self) -> None:
        """Instantiate and register all built-in plugins."""
        for cls_path in [
            ("plugins.yt_dlp_plugin",      "YtDlpPlugin"),
            ("plugins.hls_plugin",          "HLSPlugin"),
            ("plugins.dash_plugin",         "DASHPlugin"),
            ("plugins.browser_extension",   "BrowserExtensionPlugin"),
            ("plugins.ftp_plugin",          "FTPPlugin"),
            ("plugins.torrent_plugin",      "TorrentPlugin"),
        ]:
            mod_name, cls_name = cls_path
            try:
                import importlib
                mod = importlib.import_module(mod_name)
                self.register(getattr(mod, cls_name)())
            except Exception as exc:
                log.warning("Could not load plugin %s.%s: %s", mod_name, cls_name, exc)

    def __repr__(self) -> str:
        return f"<PluginRegistry plugins={[p.name for p in self._plugins]}>"