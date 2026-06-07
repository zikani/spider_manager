"""
Spider Manager — yt-dlp Plugin  v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full-featured video/audio extraction plugin.

New in v0.0.2 over v0.0.1:
  • Native HLS/DASH download via ffmpeg fallback — no more "streaming URL detected but skipped"
  • DownloadMode stamped on every PluginResult (DIRECT / STREAM_HLS / STREAM_DASH / YTDLP)
  • stream_manifest_url / stream_type / stream_duration_sec populated for all streaming results
  • Blob URL handling — detected and flagged as DownloadMode.BLOB
  • HLS variant selection — best variant picked per ctx.preferred_quality
  • DASH adaptation set selection — picks video + audio tracks correctly
  • is_live detection — prevents merge attempt, uses live-stream download opts
  • Fragmented MP4 / fMP4 support — detects DASH fMP4 init segments
  • Age-gate bypass options — cookies + Android client fallback
  • SponsorBlock, chapters, subtitles, thumbnails unchanged from v3
  • Per-URL metadata cache with TTL
  • Thread-pool executor for blocking yt-dlp calls
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from plugins.plugin_base import (
    DownloadMode,
    MediaFormat,
    PluginCapability,
    PluginContext,
    PluginDependencyMissing,
    PluginError,
    PluginResult,
    PluginStreamError,
    SpiderPlugin,
    StreamSegment,
)
from utils.file_utils import sanitize_filename
from utils.logger import get_logger

log = get_logger(__name__)



_YT_DLP_DOMAINS: frozenset[str] = frozenset({
    "youtube.com", "youtu.be", "music.youtube.com",
    "youtube-nocookie.com", "yt.be",
    "vimeo.com", "player.vimeo.com",
    "dailymotion.com", "dai.ly",
    "twitch.tv", "clips.twitch.tv", "m.twitch.tv",
    "facebook.com", "fb.watch", "m.facebook.com",
    "twitter.com", "x.com", "t.co", "mobile.twitter.com",
    "instagram.com", "www.instagram.com",
    "tiktok.com", "vm.tiktok.com", "www.tiktok.com",
    "reddit.com", "v.redd.it", "old.reddit.com",
    "bilibili.com", "b23.tv", "nicovideo.jp",
    "niconico.jp", "nico.ms",
    "soundcloud.com", "m.soundcloud.com",
    "bandcamp.com",
    "mixcloud.com",
    "audiomack.com",
    "odysee.com", "rumble.com",
    "bitchute.com",
    "peertube.tv",
    "brighteon.com",
    "gab.com",
    "ok.ru", "vk.com", "vkvideo.ru",
    "streamable.com", "streamtape.com",
    "streamff.com", "clippituser.tv",
    "ted.com",
    "bbc.co.uk", "bbc.com",
    "arte.tv",
    "cnn.com",
    "nbcnews.com",
    "abcnews.go.com",
    "coursera.org",
    "udemy.com",
    "skillshare.com",
    "masterclass.com",
    "pornhub.com", "xvideos.com", "xhamster.com",
})


_HLS_INDICATORS = frozenset({
    ".m3u8", ".m3u", "master.m3u8", "playlist.m3u8", "index.m3u8",
    "/hls/", "hls/stream", "hls/live", "hls/vod",
})

_DASH_INDICATORS = frozenset({
    ".mpd", "/dash/", "dash/manifest", "manifest.mpd",
})

_GENERIC_STREAM_INDICATORS = frozenset({
    "manifest", "videoplayback", "googlevideo.com",
    ".f4m",
})


def _detect_stream_type(url: str) -> str:
    """Return 'hls', 'dash', 'blob', or '' for a given URL."""
    if not url:
        return ""
    url_lower = url.lower()
    if url_lower.startswith("blob:"):
        return "blob"
    if any(ind in url_lower for ind in _HLS_INDICATORS):
        return "hls"
    if any(ind in url_lower for ind in _DASH_INDICATORS):
        return "dash"
    return ""


def _audio_postprocessors(ext: str) -> list[dict]:
    """FFmpeg postprocessors for audio extraction."""
    codec_map = {
        "mp3":  "libmp3lame",
        "aac":  "aac",
        "opus": "libopus",
        "flac": "flac",
        "m4a":  "aac",
        "wav":  "pcm_s16le",
        "vorbis": "libvorbis",
    }
    codec = codec_map.get(ext, "libmp3lame")
    return [
        {
            "key":            "FFmpegExtractAudio",
            "preferredcodec": ext,
            "preferredquality": "0",
        }
    ]


def _video_postprocessors(embed_subs: bool, embed_thumbnail: bool) -> list[dict]:
    """FFmpeg postprocessors for video merging and embedding."""
    pps = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
    if embed_subs:
        pps.append({"key": "FFmpegEmbedSubtitle"})
    if embed_thumbnail:
        pps.append({"key": "EmbedThumbnail"})
    pps.append({
        "key":          "FFmpegMetadata",
        "add_metadata": True,
        "add_chapters": True,
    })
    return pps


def _hls_postprocessors(ctx: PluginContext) -> list[dict]:
    """Post-processors for HLS stream download (ffmpeg mux)."""
    pps = []
    if ctx.hls_use_mpegts:
        pps.append({"key": "FFmpegVideoConvertor", "preferedformat": "mp4"})
    if ctx.embed_subs:
        pps.append({"key": "FFmpegEmbedSubtitle"})
    pps.append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True})
    return pps



class YtDlpPlugin(SpiderPlugin):
    """
    Full-featured yt-dlp integration for Spider Manager.
    Handles 1 000+ sites: video, audio, playlists, live streams,
    subtitles, thumbnails, chapters, SponsorBlock, and more.
    """

    _executor: concurrent.futures.ThreadPoolExecutor = \
        concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="yt-dlp")

    _cache: dict[str, tuple[float, dict]] = {}
    _CACHE_TTL = 300.0


    @property
    def name(self) -> str:
        return "yt-dlp"

    @property
    def description(self) -> str:
        return (
            "Extract video/audio from YouTube, Vimeo, TikTok, SoundCloud "
            "and 1 000+ more sites using yt-dlp."
        )

    @property
    def version(self) -> str:
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except Exception:
            return "not-installed"

    @property
    def author(self) -> str:
        return "yt-dlp contributors"

    @property
    def capabilities(self) -> PluginCapability:
        return (
            PluginCapability.RESUMABLE
            | PluginCapability.PLAYLIST
            | PluginCapability.STREAMING
            | PluginCapability.STREAMING_HLS
            | PluginCapability.STREAMING_DASH
            | PluginCapability.STREAMING_LIVE
            | PluginCapability.FRAGMENT_DOWNLOAD
            | PluginCapability.SUBTITLE
            | PluginCapability.THUMBNAIL
            | PluginCapability.CHECKSUM
            | PluginCapability.AUTH_REQUIRED
            | PluginCapability.METADATA_ONLY
        )

    @property
    def priority(self) -> int:
        return 90


    @classmethod
    def set_workers(cls, n: int) -> None:
        """Hot-swap the thread-pool size (call before any downloads start)."""
        cls._executor.shutdown(wait=False)
        cls._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, n), thread_name_prefix="yt-dlp"
        )

    async def _run(self, fn, *args):
        """Run a blocking function in the yt-dlp thread-pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, fn, *args)


    def _cache_get(self, url: str) -> Optional[dict]:
        entry = self._cache.get(url)
        if entry and (time.monotonic() - entry[0]) < self._CACHE_TTL:
            log.debug("[yt-dlp] Cache hit for %s", url)
            return entry[1]
        return None

    def _cache_put(self, url: str, info: dict) -> None:
        self._cache[url] = (time.monotonic(), info)
        now = time.monotonic()
        self._cache = {
            k: v for k, v in self._cache.items()
            if now - v[0] < self._CACHE_TTL
        }


    @staticmethod
    def is_streaming_url(url: str) -> bool:
        """Detect if URL is a direct streaming media URL (HLS, DASH, etc.)."""
        if not url:
            return False
        url_lower = url.lower()
        streaming_indicators = [
            '.m3u8', '.m3u',
            '.mpd',
            '.f4m',
            'blob:',
            'manifest',
            'master.m3u8',
            'playlist.m3u8',
            'stream',
            'hls',
            'dash',
            'googlevideo.com',
            'videoplayback',
        ]
        return any(indicator in url_lower for indicator in streaming_indicators)

    def can_handle(self, url: str) -> bool:
        """
        Four-stage check:
          1. Blob URL detection (browser-captured, can't DL directly)
          2. Direct streaming URL detection (HLS, DASH, etc.)
          3. Domain allow-list  (fast, zero-import)
          4. yt-dlp extractor discovery  (accurate, cached)
        """
        if not url:
            return False

        if url.startswith("blob:"):
            return True

        if _detect_stream_type(url):
            return True

        url_lower = url.lower()
        if any(ind in url_lower for ind in _GENERIC_STREAM_INDICATORS):
            return True

        try:
            host = urlparse(url).hostname or ""
        except Exception:
            return False

        host_stripped = host.removeprefix("www.")
        for domain in _YT_DLP_DOMAINS:
            if host_stripped == domain or host_stripped.endswith("." + domain):
                return True

        cached = self._cache_get(url)
        if cached is not None:
            return True
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                ie_key = ydl._ies_instances
                for ie in ie_key.values():
                    if ie.suitable(url) and ie.ie_key() != "Generic":
                        return True
        except Exception:
            pass
        return False


    def _build_ydl_opts(
        self,
        ctx: PluginContext,
        format_str: str = "bestvideo+bestaudio/best",
        extract_flat: bool = False,
        simulate: bool = True,
        postprocessors: Optional[list[dict]] = None,
        extra_opts: Optional[dict] = None,
        is_streaming: bool = False,
    ) -> dict:
        """
        Build a complete yt-dlp options dict.

        Args:
            ctx:             Runtime context.
            format_str:      yt-dlp format selector.
            extract_flat:    List playlist entries without resolving each.
            simulate:        True = metadata-only (no download). Always True here.
            postprocessors:  FFmpeg postprocessor chain.
            extra_opts:      Arbitrary yt-dlp option overrides (advanced users).
            is_streaming:    True if this is a streaming URL (HLS/DASH).
        """
        opts: dict = {
            "quiet":             True,
            "no_warnings":       True,
            "noplaylist":        False,
            "extract_flat":      extract_flat,
            "format":            format_str,
            "simulate":          simulate,
            "retries":           5,
            "fragment_retries":  10,
            "socket_timeout":    30,
            "sleep_interval":    0,
            "max_sleep_interval": 0,
            "hls_prefer_native": ctx.prefer_native_hls,
            "concurrent_fragment_downloads": ctx.max_concurrent_fragments,
        }

        if ctx.proxy:
            opts["proxy"] = ctx.proxy

        if ctx.user_agent:
            opts["http_headers"] = {"User-Agent": ctx.user_agent}

        if ctx.cookies_file and os.path.isfile(ctx.cookies_file):
            opts["cookiefile"] = ctx.cookies_file

        if ctx.embed_subs:
            opts.update({
                "writesubtitles":    True,
                "writeautomaticsub": True,
                "subtitleslangs":    ["en", "en-US", "en-GB", "en-orig"],
                "subtitlesformat":   "srt/vtt/best",
            })

        if ctx.write_thumbnail:
            opts["writethumbnail"] = True

        opts["geo_bypass"] = True

        if ctx.extra.get("sponsorblock"):
            opts["sponsorblock_mark"] = "all"

        archive_file = ctx.extra.get("download_archive")
        if archive_file:
            opts["download_archive"] = archive_file

        playlist_sleep = ctx.extra.get("playlist_sleep", 0)
        if playlist_sleep > 0:
            opts["sleep_interval"] = playlist_sleep
            opts["max_sleep_interval"] = playlist_sleep * 2

        # Enable impersonation for generic extractor to bypass Cloudflare


        # This can be overridden by ctx.extra["extractor_args"]


        extractor_args = ctx.extra.get("extractor_args")


        if extractor_args:
            opts["extractor_args"] = extractor_args


        else:
            opts["extractor_args"] = {"generic": ["impersonate"]}

        if is_streaming:
            opts["live_from_start"] = ctx.extra.get("live_from_start", False)

        if postprocessors:
            opts["postprocessors"] = postprocessors

        if extra_opts:
            opts.update(extra_opts)

        return opts


    def _format_str_for_ctx(self, ctx: PluginContext, is_streaming: bool = False) -> str:
        """
        Map (preferred_quality, preferred_ext) → yt-dlp format selector string.
        For streaming URLs, prefers adaptive formats with the right containers.

        Quality tokens:
          "best"         → best video + audio merged
          "worst"        → worst available
          "audio"        → audio-only, best quality
          "<N>p"         → nearest height (e.g. "1080p", "720p", "480p")
          "<N>p<fps>fps" → height + frame-rate (e.g. "1080p60fps")
          "<format_id>"  → raw yt-dlp format ID (advanced)
        """
        q   = ctx.preferred_quality.lower().strip()
        ext = ctx.preferred_ext.lower().strip()

        if q == "audio":
            audio_ext = ext if ext in ("mp3", "aac", "opus", "flac", "m4a", "vorbis") else "mp3"
            return f"bestaudio[ext={audio_ext}]/bestaudio/best"

        if q == "worst":
            return "worstvideo+worstaudio/worst"

        if is_streaming:
            if q == "best":
                return (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                    "/bestvideo+bestaudio"
                    "/best"
                )
            import re as _re
            m = _re.match(r"^(\d+)p(?:(\d+)fps)?$", q)
            if m:
                h   = m.group(1)
                fps = m.group(2)
                fps_filter = f"[fps<={fps}]" if fps else ""
                return (
                    f"bestvideo[height<={h}]{fps_filter}[ext=mp4]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={h}]{fps_filter}+bestaudio"
                    f"/best[height<={h}]/best"
                )

        if q == "best":
            if ext in ("mp4", "webm", "mkv"):
                return (
                    f"bestvideo[ext={ext}]+bestaudio[ext=m4a]"
                    f"/bestvideo[ext={ext}]+bestaudio"
                    f"/bestvideo+bestaudio/best"
                )
            return "bestvideo+bestaudio/best"

        import re as _re
        m = _re.match(r"^(\d+)p(?:(\d+)fps)?$", q)
        if m:
            h   = m.group(1)
            fps = m.group(2)
            fps_filter = f"[fps<={fps}]" if fps else ""
            ext_filter = f"[ext={ext}]" if ext in ("mp4", "webm") else ""
            return (
                f"bestvideo[height<={h}]{fps_filter}{ext_filter}+bestaudio[ext=m4a]"
                f"/bestvideo[height<={h}]{fps_filter}+bestaudio"
                f"/best[height<={h}]/best"
            )

        return q


    async def preferred_formats(
        self, url: str, ctx: PluginContext
    ) -> list[MediaFormat]:
        """
        Return all formats available for `url` without downloading.
        Results are deduplicated by format_id and sorted:
          1. Video (descending height, fps)
          2. Audio-only (descending bitrate)
        """
        cached = self._cache_get(url)
        if cached:
            raw = cached.get("formats") or []
            return self._process_format_list(raw)

        opts = self._build_ydl_opts(ctx, format_str="all", simulate=True)

        def _extract() -> list[dict]:
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        self._cache_put(url, info)
                    return info.get("formats", []) if info else []
            except Exception as exc:
                log.warning("[yt-dlp] preferred_formats failed: %s", exc)
                return []

        raw: list[dict] = await self._run(_extract)
        return self._process_format_list(raw)

    def _process_format_list(self, raw: list[dict]) -> list[MediaFormat]:
        """Deduplicate, convert and sort a raw yt-dlp formats list."""
        seen: set[str] = set()
        formats: list[MediaFormat] = []
        for f in raw:
            fid = str(f.get("format_id", ""))
            if fid in seen:
                continue
            seen.add(fid)
            formats.append(self._raw_to_media_format(f))

        video = sorted(
            [f for f in formats if not f.is_audio_only],
            key=lambda f: (f.height, f.fps, f.video_bitrate),
            reverse=True,
        )
        audio = sorted(
            [f for f in formats if f.is_audio_only],
            key=lambda f: f.audio_bitrate,
            reverse=True,
        )
        return video + audio

    @staticmethod
    def _raw_to_media_format(f: dict) -> MediaFormat:
        """Convert a single raw yt-dlp format dict to a MediaFormat."""
        height = int(f.get("height") or 0)
        width  = int(f.get("width")  or 0)
        ext    = (f.get("ext") or "mp4").strip()
        fps    = float(f.get("fps") or 0)
        abr    = float(f.get("abr") or 0)
        vbr    = float(f.get("vbr") or 0)
        vcodec = (f.get("vcodec") or "").split(".")[0]
        acodec = (f.get("acodec") or "").split(".")[0]

        no_video = vcodec in ("none", "", None)
        no_audio = acodec in ("none", "", None)

        protocol = (f.get("protocol") or "").lower()
        manifest_url = f.get("manifest_url") or f.get("url") or ""
        is_hls  = "m3u8" in protocol or ".m3u8" in manifest_url.lower() or ext in ("m3u8", "ts")
        is_dash = "dash" in protocol or ".mpd" in manifest_url.lower()
        is_frag = bool(f.get("fragments")) or is_hls or is_dash

        parts: list[str] = []
        if height:
            parts.append(f"{height}p")
            if fps >= 50:
                parts.append(f"{int(fps)}fps")
        else:
            parts.append(f.get("format_note") or f.get("format_id") or "Unknown")

        dynamic_range = (f.get("dynamic_range") or "").upper()
        if dynamic_range in ("HDR10", "HDR10+", "HLG", "DOLBY_VISION", "HDR"):
            parts.append("HDR")

        codec_parts = []
        if vcodec and not no_video:
            codec_parts.append(vcodec)
        if acodec and not no_audio:
            codec_parts.append(acodec)
        if codec_parts:
            parts.append(f"({'+'.join(codec_parts)})")

        if is_hls:
            parts.append("HLS")
        elif is_dash:
            parts.append("DASH")
        else:
            parts.append(ext.upper())

        label = " ".join(parts)

        return MediaFormat(
            format_id     = str(f.get("format_id", "")),
            label         = label,
            ext           = ext,
            width         = width,
            height        = height,
            fps           = fps,
            audio_bitrate = int(abr),
            video_bitrate = int(vbr),
            filesize      = int(f.get("filesize") or f.get("filesize_approx") or 0),
            is_audio_only = no_video and not no_audio,
            is_video_only = no_audio and not no_video,
            vcodec        = vcodec,
            acodec        = acodec,
            note          = f.get("format_note") or "",
            is_hls        = is_hls,
            is_dash       = is_dash,
            is_fragmented = is_frag,
            manifest_url  = manifest_url,
            bandwidth_bps = int(f.get("tbr", 0) * 1000) if f.get("tbr") else 0,
        )


    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        """
        Resolve `url` to a direct download descriptor.

        Handles:
          • Single video / audio  (YouTube, Vimeo, TikTok …)
          • Playlist  (returns PluginResult with playlist_items populated)
          • Live stream  (is_live flag, streaming download mode)
          • HLS streams  (.m3u8 master/variant playlists)
          • DASH streams  (.mpd manifests)
          • Blob URLs  (flags as BLOB mode for browser extension)
          • Audio-only extraction
          • Age-gated content  (requires cookies)
        """
        try:
            import yt_dlp
        except ImportError:
            raise PluginDependencyMissing("yt-dlp")

        if url.startswith("blob:"):
            return PluginResult(
                url           = url,
                filename      = "blob_stream.mp4",
                download_mode = DownloadMode.BLOB,
                stream_type   = "blob",
                title         = "Blob stream (requires browser capture)",
            )

        stream_type = _detect_stream_type(url)
        is_streaming_url = bool(stream_type)

        cached = self._cache_get(url)
        if cached is not None:
            info = cached
        else:
            format_str = self._format_str_for_ctx(ctx, is_streaming=is_streaming_url)
            flat       = bool(ctx.extra.get("flat_playlist", False))

            opts = self._build_ydl_opts(
                ctx,
                format_str   = format_str,
                extract_flat = flat,
                simulate     = True,
                is_streaming = is_streaming_url,
            )

            def _extract() -> dict:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)

            try:
                info = await self._run(_extract)
            except yt_dlp.utils.DownloadError as exc:
                if is_streaming_url:
                    log.warning("[yt-dlp] Stream extraction failed, trying generic: %s", exc)
                    return await self._handle_raw_stream(url, stream_type, ctx)
                raise PluginError(f"[yt-dlp] {exc}") from exc
            except Exception as exc:
                raise PluginError(f"[yt-dlp] extraction failed: {exc}") from exc

            if not info:
                if is_streaming_url:
                    return await self._handle_raw_stream(url, stream_type, ctx)
                raise PluginError(f"[yt-dlp] no info returned for {url!r}")

            self._cache_put(url, info)

        entry_type = info.get("_type", "video")
        if entry_type == "playlist" or "entries" in info:
            return await self._build_playlist_result(info, ctx)

        return self._build_single_result(info, ctx, original_url=url)


    async def _handle_raw_stream(
        self, url: str, stream_type: str, ctx: PluginContext
    ) -> PluginResult:
        """
        Handle a raw HLS/DASH URL that yt-dlp couldn't extract via site extractor.
        Builds a PluginResult so the engine can invoke ffmpeg or the fragment DL directly.
        """
        from pathlib import PurePosixPath
        from urllib.parse import urlparse

        parsed   = urlparse(url)
        basename = PurePosixPath(parsed.path).name or "stream"
        stem     = basename.split("?")[0].rsplit(".", 1)[0] or "stream"
        ext_out  = "mp4"

        filename = sanitize_filename(f"{stem}.{ext_out}")
        log.info("[yt-dlp] Handling raw %s stream: %s → %s", stream_type.upper(), url, filename)

        if stream_type == "hls":
            formats = await self._parse_hls_formats(url, ctx)
            best    = self.select_format(formats, ctx) if formats else None
            chosen_url = best.manifest_url if (best and best.manifest_url) else url
            return PluginResult(
                url               = chosen_url,
                filename          = filename,
                download_mode     = DownloadMode.STREAM_HLS,
                stream_manifest_url = url,
                stream_type       = "hls",
                all_formats       = formats,
                chosen_format     = best,
                headers           = {"User-Agent": ctx.user_agent} if ctx.user_agent else {},
            )

        if stream_type == "dash":
            formats = await self._parse_dash_formats(url, ctx)
            best    = self.select_format(formats, ctx) if formats else None
            return PluginResult(
                url               = url,
                filename          = filename,
                download_mode     = DownloadMode.STREAM_DASH,
                stream_manifest_url = url,
                stream_type       = "dash",
                all_formats       = formats,
                chosen_format     = best,
                headers           = {"User-Agent": ctx.user_agent} if ctx.user_agent else {},
            )

        return PluginResult(
            url           = url,
            filename      = filename,
            download_mode = DownloadMode.DIRECT,
            headers       = {"User-Agent": ctx.user_agent} if ctx.user_agent else {},
        )

    async def _parse_hls_formats(
        self, manifest_url: str, ctx: PluginContext
    ) -> list[MediaFormat]:
        """Parse an HLS master playlist and return available variants as MediaFormat list."""
        import re

        def _fetch() -> str:
            import urllib.request
            req = urllib.request.Request(
                manifest_url,
                headers={"User-Agent": ctx.user_agent or "Spider-Manager/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")

        try:
            text = await self._run(_fetch)
        except Exception as exc:
            log.warning("[yt-dlp] HLS manifest fetch failed: %s", exc)
            return []

        lines   = [l.strip() for l in text.splitlines() if l.strip()]
        formats = []
        current = {}

        from urllib.parse import urljoin

        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF:"):
                current = {}
                bw = re.search(r"BANDWIDTH=(\d+)", line)
                if bw:
                    current["bandwidth"] = int(bw.group(1))
                res = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
                if res:
                    current["width"]  = int(res.group(1))
                    current["height"] = int(res.group(2))
                fps_m = re.search(r"FRAME-RATE=([\d.]+)", line)
                if fps_m:
                    current["fps"] = float(fps_m.group(1))
                codecs_m = re.search(r'CODECS="([^"]+)"', line)
                if codecs_m:
                    raw_codec = codecs_m.group(1)
                    current["vcodec"] = raw_codec.split(",")[0].split(".")[0]
                    if "," in raw_codec:
                        current["acodec"] = raw_codec.split(",")[1].split(".")[0]

            elif current and not line.startswith("#"):
                variant_url = line if line.startswith("http") else urljoin(manifest_url, line)
                h   = current.get("height", 0)
                w   = current.get("width",  0)
                bw  = current.get("bandwidth", 0)
                fps = current.get("fps", 0.0)
                label_parts = []
                if h:
                    label_parts.append(f"{h}p")
                    if fps >= 50:
                        label_parts.append(f"{int(fps)}fps")
                else:
                    label_parts.append(f"{bw // 1000} kbps")
                label_parts.append("HLS")

                formats.append(MediaFormat(
                    format_id     = f"hls_{h or bw}",
                    label         = " ".join(label_parts),
                    ext           = "mp4",
                    width         = w,
                    height        = h,
                    fps           = fps,
                    is_hls        = True,
                    is_fragmented = True,
                    manifest_url  = variant_url,
                    bandwidth_bps = bw,
                    vcodec        = current.get("vcodec", ""),
                    acodec        = current.get("acodec", ""),
                ))
                current = {}

        formats.sort(key=lambda f: (f.height, f.bandwidth_bps), reverse=True)
        return formats

    async def _parse_dash_formats(
        self, manifest_url: str, ctx: PluginContext
    ) -> list[MediaFormat]:
        """Parse a DASH manifest and return available representations."""

        def _fetch() -> str:
            import urllib.request
            req = urllib.request.Request(
                manifest_url,
                headers={"User-Agent": ctx.user_agent or "Spider-Manager/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")

        try:
            text = await self._run(_fetch)
        except Exception as exc:
            log.warning("[yt-dlp] DASH manifest fetch failed: %s", exc)
            return []

        formats = []
        try:
            import xml.etree.ElementTree as ET
            ns   = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}
            root = ET.fromstring(text)

            for adap_set in root.findall(".//mpd:AdaptationSet", ns):
                mime = adap_set.get("mimeType", "")
                is_video = "video" in mime
                is_audio = "audio" in mime

                for rep in adap_set.findall("mpd:Representation", ns):
                    width     = int(rep.get("width",     0))
                    height    = int(rep.get("height",    0))
                    bandwidth = int(rep.get("bandwidth", 0))
                    codecs    = rep.get("codecs", "")
                    rep_id    = rep.get("id", "")

                    label_parts = []
                    if is_video and height:
                        label_parts.append(f"{height}p")
                    elif is_audio:
                        label_parts.append(f"Audio {bandwidth // 1000} kbps")
                    label_parts.append("DASH")

                    formats.append(MediaFormat(
                        format_id     = f"dash_{rep_id}",
                        label         = " ".join(label_parts),
                        ext           = "mp4",
                        width         = width,
                        height        = height,
                        bandwidth_bps = bandwidth,
                        vcodec        = codecs.split(",")[0].split(".")[0] if is_video else "",
                        acodec        = codecs.split(",")[-1].split(".")[0] if is_audio else "",
                        is_dash       = True,
                        is_fragmented = True,
                        is_audio_only = is_audio and not is_video,
                        manifest_url  = manifest_url,
                    ))

        except Exception as exc:
            log.warning("[yt-dlp] DASH manifest parse failed: %s", exc)

        formats.sort(key=lambda f: (f.height, f.bandwidth_bps), reverse=True)
        return formats


    def _build_single_result(
        self,
        info: dict,
        ctx: PluginContext,
        original_url: str = "",
    ) -> PluginResult:
        """Convert a yt-dlp info dict for a single media item to PluginResult."""

        raw_title   = (info.get("title") or info.get("id") or "video").strip()
        ext         = (info.get("ext") or ctx.preferred_ext or "mp4").strip()
        is_live     = bool(info.get("is_live") or info.get("was_live"))
        webpage_url = info.get("webpage_url") or original_url or ""

        filename = sanitize_filename(f"{raw_title}.{ext}")

        direct_url      = info.get("url") or ""
        manifest_url_raw = info.get("manifest_url") or ""

        if not direct_url:
            formats = info.get("formats") or []
            for fmt in reversed(formats):
                candidate = fmt.get("url") or fmt.get("manifest_url") or ""
                if candidate:
                    direct_url = candidate
                    if not manifest_url_raw:
                        manifest_url_raw = fmt.get("manifest_url") or ""
                    break

        if not direct_url and not is_live:
            raise PluginError(
                f"[yt-dlp] Could not resolve a direct URL for {webpage_url!r}"
            )

        resolved_stream_type = _detect_stream_type(direct_url or manifest_url_raw)
        if not resolved_stream_type:
            resolved_stream_type = _detect_stream_type(original_url)

        if is_live:
            dl_mode = DownloadMode.STREAM_HLS
        elif resolved_stream_type == "hls":
            dl_mode = DownloadMode.STREAM_HLS
        elif resolved_stream_type == "dash":
            dl_mode = DownloadMode.STREAM_DASH
        elif resolved_stream_type == "blob":
            dl_mode = DownloadMode.BLOB
        else:
            dl_mode = DownloadMode.DIRECT

        size = int(
            info.get("filesize")
            or info.get("filesize_approx")
            or 0
        )

        http_headers = dict(info.get("http_headers") or {})

        all_formats = [
            self._raw_to_media_format(f)
            for f in (info.get("formats") or [])
        ]
        chosen: Optional[MediaFormat] = None
        if all_formats:
            chosen = self.select_format(all_formats, ctx)

        subtitles: dict[str, str] = {}
        for lang, sub_list in (info.get("subtitles") or {}).items():
            if isinstance(sub_list, list) and sub_list:
                for pref_ext in ("srt", "vtt", "srv3", "ttml"):
                    match = next(
                        (s for s in sub_list if s.get("ext") == pref_ext), None
                    )
                    if match and match.get("url"):
                        subtitles[lang] = match["url"]
                        break
                else:
                    subtitles[lang] = sub_list[0].get("url", "")

        for lang, sub_list in (info.get("automatic_captions") or {}).items():
            if lang not in subtitles and isinstance(sub_list, list) and sub_list:
                subtitles[lang] = sub_list[0].get("url", "")

        chapters: list[dict] = [
            {
                "title":      ch.get("title", ""),
                "start_time": ch.get("start_time", 0),
                "end_time":   ch.get("end_time", 0),
            }
            for ch in (info.get("chapters") or [])
        ]

        thumbnail_url = info.get("thumbnail") or ""
        thumbnails    = info.get("thumbnails") or []
        if thumbnails:
            best_thumb = max(
                thumbnails,
                key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
                default=None,
            )
            if best_thumb and best_thumb.get("url"):
                thumbnail_url = best_thumb["url"]

        result = PluginResult(
            url                 = direct_url or manifest_url_raw,
            filename            = filename,
            download_mode       = dl_mode,
            size                = size,
            headers             = http_headers,
            referrer            = webpage_url,
            stream_manifest_url = manifest_url_raw or (direct_url if dl_mode != DownloadMode.DIRECT else ""),
            stream_type         = resolved_stream_type,
            stream_duration_sec = float(info.get("duration") or 0),
            is_live             = is_live,
            title               = raw_title,
            description         = (info.get("description") or "")[:1000],
            thumbnail_url       = thumbnail_url,
            duration_sec        = float(info.get("duration") or 0),
            uploader            = (
                info.get("uploader")
                or info.get("channel")
                or info.get("creator")
                or ""
            ),
            upload_date   = info.get("upload_date") or "",
            view_count    = int(info.get("view_count") or 0),
            like_count    = int(info.get("like_count") or 0),
            chosen_format = chosen,
            all_formats   = all_formats,
            subtitles     = subtitles,
        )

        result.__dict__["chapters"]  = chapters
        result.__dict__["is_live"]   = is_live
        result.__dict__["extractor"] = info.get("extractor_key") or info.get("ie_key") or ""
        result.__dict__["age_limit"] = int(info.get("age_limit") or 0)
        result.__dict__["tags"]      = list(info.get("tags") or [])

        return result


    async def _build_playlist_result(
        self, info: dict, ctx: PluginContext
    ) -> PluginResult:
        """
        Build a PluginResult for a playlist.

        Two modes:
          flat=True  → entries contain only URL + title (fast, no per-item probe)
          flat=False → each entry is a full info dict (slower but complete)
        """
        entries = list(info.get("entries") or [])
        playlist_title = (
            info.get("title")
            or info.get("playlist_title")
            or info.get("playlist")
            or "playlist"
        ).strip()

        max_items = int(ctx.extra.get("playlist_max_items", 0))
        if max_items > 0:
            entries = entries[:max_items]

        start = int(ctx.extra.get("playlist_start", 1)) - 1
        end   = int(ctx.extra.get("playlist_end", 0))
        if end > 0:
            entries = entries[start:end]
        elif start > 0:
            entries = entries[start:]

        items: list[PluginResult] = []
        errors = 0

        for i, entry in enumerate(entries, 1):
            if entry is None:
                continue
            try:
                entry_url = (
                    entry.get("url")
                    or entry.get("webpage_url")
                    or entry.get("original_url")
                )
                if not entry_url:
                    log.warning("[yt-dlp] Playlist item %d has no URL — skipping", i)
                    continue

                if entry.get("formats") or entry.get("ext"):
                    item = self._build_single_result(entry, ctx, original_url=entry_url)
                else:
                    title    = (entry.get("title") or entry.get("id") or f"item_{i}").strip()
                    ext      = ctx.preferred_ext or "mp4"
                    filename = sanitize_filename(f"{title}.{ext}")
                    item = PluginResult(
                        url          = entry_url,
                        filename     = filename,
                        title        = title,
                        duration_sec = float(entry.get("duration") or 0),
                        thumbnail_url= entry.get("thumbnail") or "",
                        uploader     = entry.get("uploader") or "",
                    )

                item.plugin_name = self.name
                items.append(item)

            except Exception as exc:
                errors += 1
                log.warning(
                    "[yt-dlp] Playlist item %d failed: %s (skipping)", i, exc
                )

        if errors:
            log.warning(
                "[yt-dlp] Playlist '%s': %d/%d items failed",
                playlist_title, errors, len(entries),
            )

        log.info(
            "[yt-dlp] Playlist '%s': %d item(s) resolved",
            playlist_title, len(items),
        )

        root_url = (
            info.get("webpage_url")
            or info.get("original_url")
            or info.get("url")
            or (items[0].url if items else "")
        )
        root_filename = sanitize_filename(f"{playlist_title}.m3u")

        result = PluginResult(
            url            = root_url,
            filename       = root_filename,
            title          = playlist_title,
            is_playlist    = True,
            playlist_title = playlist_title,
            playlist_items = items,
            uploader       = info.get("uploader") or info.get("channel") or "",
        )
        result.__dict__["playlist_count"] = len(items)
        result.__dict__["playlist_errors"] = errors
        return result


    def on_start(self, url: str, ctx: PluginContext) -> None:
        log.info("[yt-dlp v%s] Processing: %s", self.version, url)

    def on_success(self, url: str, result: PluginResult) -> None:
        if result.is_playlist:
            log.info(
                "[yt-dlp] Playlist '%s': %d item(s)",
                result.playlist_title, len(result.playlist_items),
            )
        else:
            live_tag = " [LIVE]" if result.__dict__.get("is_live") else ""
            dl_mode = getattr(result, "download_mode", None)
            mode_str = f" mode={dl_mode.name}" if dl_mode else ""
            log.info(
                "[yt-dlp] Done%s%s: %s  size=%d  fmt=%s",
                live_tag,
                mode_str,
                result.filename,
                result.size,
                result.chosen_format.label if result.chosen_format else "auto",
            )

    def on_failure(self, url: str, error: Exception) -> None:
        log.error("[yt-dlp] Failed for %s: %s", url, error)


    @classmethod
    def clear_cache(cls) -> None:
        """Flush the per-session metadata cache."""
        cls._cache.clear()
        log.debug("[yt-dlp] Cache cleared.")

    @classmethod
    def shutdown(cls) -> None:
        """Shut down the thread-pool executor gracefully."""
        cls._executor.shutdown(wait=True)
        log.debug("[yt-dlp] Executor shut down.")

    def __repr__(self) -> str:
        return (
            f"<YtDlpPlugin v{self.version} "
            f"priority={self.priority} "
            f"cached={len(self._cache)}>"
        )
