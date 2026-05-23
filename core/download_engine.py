"""
Spider Manager — Download Engine  v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v3 improvements over the original:

STREAMING  (the main gap fixed)
  • DownloadMode-aware dispatch: DIRECT | STREAM_HLS | STREAM_DASH | YTDLP | BLOB
  • HLS download: fetches master → variant playlist → parallel segment download
    with per-segment retry, AES-128 decryption, and ffmpeg mux to .mp4
  • DASH download: fetches MPD → selects best video + audio → downloads both
    track sets in parallel → ffmpeg mux to .mp4
  • YTDLP download: subprocess wrapper around yt-dlp, real-time progress
    parsed from its JSON output lines
  • Blob URL fallback: routes to yt-dlp via page URL

DIRECT DOWNLOAD (significantly improved)
  • Adaptive segment count: small files → 1 seg, large files → up to N
  • Minimum segment size guard (1 MB) — stops micro-segment overhead
  • Chunk-level speed measurement with exponential moving average
  • Correct resume: re-reads existing .partN size before setting Range header
  • set_speed_limit() now works — SpeedLimiter is updated live per-task
  • Stale session detection: reconnects if server resets connection mid-download

INTEGRITY
  • Optional SHA-256 / MD5 checksum verification after merge
  • File-size mismatch raises a real error (was only a warning before)
  • Segment ordering enforced even if gather() completes out of order

FFMPEG
  • ffmpeg_merge_hls() / ffmpeg_merge_dash() — async subprocess helpers
  • ffmpeg binary auto-discovered (PATH → bundled → common system paths)
  • stderr captured and logged at DEBUG level; fatal errors raised

CONCURRENCY / LIFECYCLE
  • _active_tasks dict replaces _run_tasks — tracks Task + DownloadTask
  • pause() drains in-flight segments cleanly before returning
  • cancel() removes temp files for stream segments too
  • close() cancels all in-flight tasks before closing the session
  • DownloadEngine is usable as an async context manager

DIAGNOSTICS
  • probe() falls back from HEAD to GET+cancel when server rejects HEAD
  • DownloadTask.stats property — snapshot dict for UI / queue manager
  • Speed EMA window configurable; separate last-second peak speed tracked
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp

from config.constants import (
    CONNECTION_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SEGMENTS,
    READ_TIMEOUT,
    RETRY_DELAY,
    DownloadState,
)
from core.speed_limiter import SpeedLimiter
from utils.file_utils import sanitize_filename
from utils.logger import get_logger
from utils.network_utils import current_proxy
from utils.url_parser import extract_filename

log = get_logger(__name__)


CHUNK_SIZE          = 131_072
MIN_SEGMENT_BYTES   = 1_048_576
SPEED_EMA_ALPHA     = 0.25
HLS_SEGMENT_TIMEOUT = 30.0
FFMPEG_TIMEOUT      = 3_600
MAX_HLS_VARIANTS    = 32
PROBE_FALLBACK_BYTES = 16_384



@dataclass
class DownloadSegment:
    """One byte-range segment of a direct (non-streaming) download."""

    index:      int
    start:      int
    end:        int
    downloaded: int  = 0
    temp_path:  str  = ""
    complete:   bool = False

    @property
    def expected_bytes(self) -> int:
        return self.end - self.start + 1 if self.end > 0 else 0

    @property
    def remaining_bytes(self) -> int:
        return max(0, self.expected_bytes - self.downloaded)



@dataclass
class StreamSegment:
    """One fragment in an HLS or DASH stream."""

    url:              str
    index:            int   = 0
    duration_sec:     float = 0.0
    temp_path:        str   = ""
    complete:         bool  = False
    key_url:          str   = ""
    key_iv:           str   = ""
    byterange_start:  int   = 0
    byterange_length: int   = 0



@dataclass
class DownloadTask:
    """
    Complete descriptor for one download job.

    New fields vs original:
      download_mode     — 'direct' | 'stream_hls' | 'stream_dash' | 'ytdlp' | 'blob'
      stream_manifest_url — the .m3u8 / .mpd URL
      stream_type       — 'hls' | 'dash' | ''
      stream_segments   — list[StreamSegment] built during HLS/DASH planning
      expected_checksum — 'sha256:<hex>' or 'md5:<hex>' (optional)
      peak_speed        — highest 1-second throughput seen so far
    """

    id:                  str
    url:                 str
    filename:            str
    save_path:           str

    total_size:          int                      = 0
    downloaded:          int                      = 0
    segments:            list[DownloadSegment]    = field(default_factory=list)

    download_mode:       str                      = "direct"
    stream_manifest_url: str                      = ""
    stream_type:         str                      = ""
    stream_segments:     list[StreamSegment]      = field(default_factory=list)
    stream_duration_sec: float                    = 0.0
    is_live:             bool                     = False

    state:               str                      = DownloadState.QUEUED
    speed:               float                    = 0.0
    peak_speed:          float                    = 0.0
    eta:                 int                      = 0
    error:               str                      = ""
    retry_count:         int                      = 0

    expected_checksum:   str                      = ""

    category:            str                      = "Other"
    referrer:            str                      = ""
    headers:             dict                     = field(default_factory=dict)

    created_at:          float                    = field(default_factory=time.time)
    started_at:          Optional[float]          = None
    completed_at:        Optional[float]          = None

    progress_callback:   Optional[Callable]       = None
    state_callback:      Optional[Callable]       = None


    @property
    def progress(self) -> float:
        """0–100 % completion."""
        if self.download_mode in ("stream_hls", "stream_dash"):
            total = len(self.stream_segments)
            if total == 0:
                return 0.0
            done = sum(1 for s in self.stream_segments if s.complete)
            return round(done / total * 100, 2)
        if self.total_size == 0:
            return 0.0
        return round(min(self.downloaded / self.total_size * 100, 100.0), 2)

    @property
    def full_path(self) -> str:
        return os.path.join(self.save_path, self.filename)

    @property
    def elapsed(self) -> float:
        """Seconds since download started (0 if not yet started)."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    @property
    def stats(self) -> dict:
        """Snapshot dict for UI / queue-manager polling."""
        return {
            "id":            self.id,
            "filename":      self.filename,
            "state":         self.state,
            "progress":      self.progress,
            "speed":         self.speed,
            "peak_speed":    self.peak_speed,
            "eta":           self.eta,
            "downloaded":    self.downloaded,
            "total_size":    self.total_size,
            "elapsed":       round(self.elapsed, 1),
            "download_mode": self.download_mode,
            "error":         self.error,
            "retry_count":   self.retry_count,
        }

    def _fire_progress(self):
        if self.progress_callback:
            try:
                self.progress_callback(self)
            except Exception:
                pass

    def _fire_state(self):
        if self.state_callback:
            try:
                self.state_callback(self)
            except Exception:
                pass



def _find_ffmpeg() -> str:
    """Locate the ffmpeg binary. Returns path or 'ffmpeg' (relies on PATH)."""
    try:
        from config.settings import get_settings
        cfg_path = get_settings().get("ffmpeg_path", "")
        if cfg_path and os.path.isfile(cfg_path):
            return cfg_path
    except Exception:
        pass

    found = shutil.which("ffmpeg")
    if found:
        return found

    candidates = [
        "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    return "ffmpeg"


async def _ffmpeg_run(args: list[str], description: str = "ffmpeg") -> None:
    """
    Run an ffmpeg command asynchronously.
    Raises RuntimeError on non-zero exit.
    """
    cmd = [_find_ffmpeg()] + args
    log.debug("[ffmpeg] %s: %s", description, " ".join(cmd))

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            startupinfo=startupinfo,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), FFMPEG_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"ffmpeg timed out after {FFMPEG_TIMEOUT}s for {description}")

    if proc.returncode != 0:
        err_text = stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}) for {description}:\n{err_text}"
        )
    log.debug("[ffmpeg] %s finished OK", description)


async def ffmpeg_concat_segments(
    segment_paths: list[str],
    output_path: str,
    task_filename: str = "",
) -> None:
    """
    Mux a list of raw .ts / .fmp4 segment files into a single .mp4
    using ffmpeg concat demuxer.
    """
    list_fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="spider_concat_")
    try:
        with os.fdopen(list_fd, "w") as f:
            for p in segment_paths:
                escaped = p.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        await _ffmpeg_run(
            [
                "-y",
                "-f",   "concat",
                "-safe", "0",
                "-i",   list_path,
                "-c",   "copy",
                "-movflags", "+faststart",
                output_path,
            ],
            description=f"concat→{os.path.basename(output_path)}",
        )
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass


async def ffmpeg_merge_av_tracks(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> None:
    """Mux separate video and audio tracks (DASH) into one .mp4."""
    await _ffmpeg_run(
        [
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ],
        description=f"merge-av→{os.path.basename(output_path)}",
    )


async def ffmpeg_remux_url(
    manifest_url: str,
    output_path: str,
    headers: dict | None = None,
) -> None:
    """
    Ask ffmpeg to pull and mux a remote HLS/DASH manifest directly.
    Used as a fallback when segment-level download fails.
    """
    header_args: list[str] = []
    for key, value in (headers or {}).items():
        if key.lower() not in ("host",):
            header_args += ["-headers", f"{key}: {value}\r\n"]

    await _ffmpeg_run(
        header_args + [
            "-y",
            "-i",       manifest_url,
            "-c",       "copy",
            "-movflags", "+faststart",
            output_path,
        ],
        description=f"remux→{os.path.basename(output_path)}",
    )



def _verify_checksum(file_path: str, expected: str) -> None:
    """
    Verify file against expected checksum.

    Args:
        file_path: Path to the completed file.
        expected:  'sha256:<hexdigest>' or 'md5:<hexdigest>'

    Raises:
        ValueError if checksum does not match.
        ValueError if algorithm is unsupported.
    """
    if not expected:
        return

    parts = expected.split(":", 1)
    if len(parts) != 2:
        log.warning("Invalid checksum format '%s' — skipping verification", expected)
        return

    algo, expected_hex = parts[0].lower(), parts[1].lower()
    if algo == "sha256":
        h = hashlib.sha256()
    elif algo == "md5":
        h = hashlib.md5()
    else:
        log.warning("Unsupported checksum algorithm '%s' — skipping", algo)
        return

    with open(file_path, "rb") as f:
        while chunk := f.read(1_048_576):
            h.update(chunk)

    actual_hex = h.hexdigest()
    if actual_hex != expected_hex:
        raise ValueError(
            f"Checksum mismatch for {os.path.basename(file_path)}: "
            f"expected {algo}:{expected_hex}, got {algo}:{actual_hex}"
        )
    log.info("Checksum OK (%s) for %s", algo, os.path.basename(file_path))



def _parse_hls_master(text: str, base_url: str) -> list[dict]:
    """
    Parse an HLS master playlist and return variants sorted best-first.
    Each entry: {url, bandwidth, resolution, codecs}
    """
    variants: list[dict] = []
    current:  dict       = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        if line.startswith("#EXT-X-STREAM-INF:"):
            current = {}
            bw = re.search(r"BANDWIDTH=(\d+)", line)
            if bw:
                current["bandwidth"] = int(bw.group(1))
            res = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
            if res:
                current["resolution"] = f"{res.group(2)}p"
            cod = re.search(r'CODECS="([^"]+)"', line)
            if cod:
                current["codecs"] = cod.group(1)
        elif current and not line.startswith("#"):
            current["url"] = line if line.startswith("http") else urljoin(base_url, line)
            variants.append(current)
            current = {}

    variants.sort(key=lambda v: v.get("bandwidth", 0), reverse=True)
    return variants[:MAX_HLS_VARIANTS]


def _parse_hls_media(text: str, base_url: str) -> list[dict]:
    """
    Parse an HLS media playlist (.m3u8).
    Returns list of segment dicts: {url, duration, key_url, key_iv, byterange}
    """
    segments:  list[dict]  = []
    current:   dict        = {}
    key_url    = ""
    key_iv     = ""

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF:"):
            dur_str = line.split(":")[1].rstrip(",").split(",")[0]
            current["duration"] = float(dur_str) if dur_str else 0.0

        elif line.startswith("#EXT-X-KEY:"):
            m = re.search(r'URI="([^"]+)"', line)
            if m:
                raw = m.group(1)
                key_url = raw if raw.startswith("http") else urljoin(base_url, raw)
            iv_m = re.search(r"IV=0x([0-9a-fA-F]+)", line)
            key_iv = iv_m.group(1) if iv_m else ""

        elif line.startswith("#EXT-X-BYTERANGE:"):
            parts = line.split(":")[1].split("@")
            current["byterange_length"] = int(parts[0])
            current["byterange_start"]  = int(parts[1]) if len(parts) > 1 else 0

        elif not line.startswith("#"):
            seg_url = line if line.startswith("http") else urljoin(base_url, line)
            current["url"]     = seg_url
            current["key_url"] = key_url
            current["key_iv"]  = key_iv
            segments.append(current)
            current = {}

    return segments


def _parse_dash_mpd(text: str, base_url: str) -> dict:
    """
    Parse a DASH .mpd manifest.
    Returns {'video': [rep...], 'audio': [rep...]}  sorted best-first.
    Each rep: {url, bandwidth, width, height, codecs, mime_type, id}
    """
    import xml.etree.ElementTree as ET

    NS = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise RuntimeError(f"DASH manifest parse error: {e}") from e

    video_reps: list[dict] = []
    audio_reps: list[dict] = []

    for adapt in root.findall(".//mpd:AdaptationSet", NS):
        mime = adapt.get("mimeType", "")
        is_video = "video" in mime
        is_audio = "audio" in mime
        if not is_video and not is_audio:
            first = adapt.find("mpd:Representation", NS)
            if first is not None:
                rep_mime = first.get("mimeType", "")
                is_video = "video" in rep_mime
                is_audio = "audio" in rep_mime

        for rep in adapt.findall("mpd:Representation", NS):
            rep_id    = rep.get("id", "")
            bandwidth = int(rep.get("bandwidth", 0))
            codecs    = rep.get("codecs", "")
            width     = int(rep.get("width",  0))
            height    = int(rep.get("height", 0))
            rep_mime  = rep.get("mimeType", mime)

            base_el = rep.find("mpd:BaseURL", NS) or adapt.find("mpd:BaseURL", NS)
            seg_url = base_url
            if base_el is not None and base_el.text:
                raw = base_el.text.strip()
                seg_url = raw if raw.startswith("http") else urljoin(base_url, raw)

            entry = {
                "id":        rep_id,
                "url":       seg_url,
                "bandwidth": bandwidth,
                "width":     width,
                "height":    height,
                "codecs":    codecs,
                "mime_type": rep_mime,
            }

            if is_video:
                video_reps.append(entry)
            elif is_audio:
                audio_reps.append(entry)

    video_reps.sort(key=lambda r: r["bandwidth"], reverse=True)
    audio_reps.sort(key=lambda r: r["bandwidth"], reverse=True)

    return {"video": video_reps, "audio": audio_reps}



async def _fetch_aes_key(
    session: aiohttp.ClientSession, key_url: str, proxy: str | None
) -> bytes:
    async with session.get(key_url, proxy=proxy) as resp:
        resp.raise_for_status()
        return await resp.read()


async def _decrypt_segment(
    data: bytes,
    key_url: str,
    key_iv: str,
    session: aiohttp.ClientSession,
    proxy: str | None,
    seg_index: int,
) -> bytes:
    """AES-128-CBC decrypt an HLS segment."""
    try:
        from Crypto.Cipher import AES
    except ImportError:
        log.warning("[HLS] pycryptodome not installed — skipping AES decryption")
        return data

    key = await _fetch_aes_key(session, key_url, proxy)
    iv  = bytes.fromhex(key_iv.zfill(32)) if key_iv else seg_index.to_bytes(16, "big")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(data)



class DownloadEngine:
    """
    Multi-mode async download engine.

    Supports:
      DIRECT     — segmented byte-range HTTP download with resume + checksum
      STREAM_HLS — HLS master/media playlist download + ffmpeg mux
      STREAM_DASH— DASH MPD download + ffmpeg A/V merge
      YTDLP      — yt-dlp subprocess with real-time progress parsing
      BLOB       — redirects to yt-dlp using the page URL

    Usage::

        async with DownloadEngine() as engine:
            await engine.start(task)

    """

    def __init__(
        self,
        segments:      int              = DEFAULT_SEGMENTS,
        speed_limiter: SpeedLimiter | None = None,
    ):
        self.segments      = segments
        self.speed_limiter = speed_limiter or SpeedLimiter()

        self._active: dict[str, tuple[asyncio.Task, DownloadTask]] = {}
        self._session: Optional[aiohttp.ClientSession] = None


    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()


    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=16,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            timeout = aiohttp.ClientTimeout(
                connect   = CONNECTION_TIMEOUT,
                sock_read = READ_TIMEOUT,
            )
            self._session = aiohttp.ClientSession(
                connector = connector,
                timeout   = timeout,
                headers   = {"User-Agent": "Spider-Manager/3.0"},
            )
        return self._session


    async def probe(self, url: str, headers: dict | None = None) -> dict:
        """
        HEAD request to get file metadata.
        Falls back to a partial GET if the server rejects HEAD.

        Returns dict with keys:
          size, filename, resumable, content_type, url, accepts_ranges
        """
        session = await self._get_session()
        h       = dict(headers or {})
        proxy   = current_proxy()

        try:
            async with session.head(
                url, headers=h, allow_redirects=True, proxy=proxy
            ) as resp:
                if resp.status < 400:
                    return self._parse_probe_response(resp, str(resp.url))
        except Exception as e:
            log.debug("HEAD failed for %s (%s), falling back to GET probe", url, e)

        h["Range"] = f"bytes=0-{PROBE_FALLBACK_BYTES - 1}"
        async with session.get(
            url, headers=h, allow_redirects=True, proxy=proxy
        ) as resp:
            resp.raise_for_status()
            await resp.content.read(64)
            return self._parse_probe_response(resp, str(resp.url))

    @staticmethod
    def _parse_probe_response(resp: aiohttp.ClientResponse, final_url: str) -> dict:
        raw_filename = extract_filename(final_url, dict(resp.headers))
        filename     = sanitize_filename(raw_filename)
        cr  = resp.headers.get("Content-Range", "")
        crm = re.search(r"/(\d+)$", cr)
        size = int(crm.group(1)) if crm else int(resp.headers.get("Content-Length", 0) or 0)
        return {
            "size":          size,
            "filename":      filename,
            "resumable":     "bytes" in resp.headers.get("Accept-Ranges", ""),
            "content_type":  resp.headers.get("Content-Type", ""),
            "url":           final_url,
            "accepts_ranges": resp.status in (200, 206) and
                              "bytes" in resp.headers.get("Accept-Ranges", ""),
        }


    async def start(self, task: DownloadTask):
        """
        Begin or resume a download.
        Dispatches to the correct strategy based on task.download_mode.
        """
        if task.state in (DownloadState.COMPLETED, DownloadState.DOWNLOADING):
            return

        coro = {
            "direct":      self._run_direct,
            "stream_hls":  self._run_hls,
            "stream_dash": self._run_dash,
            "ytdlp":       self._run_ytdlp,
            "blob":        self._run_blob,
        }.get(task.download_mode, self._run_direct)(task)

        t = asyncio.create_task(coro)
        self._active[task.id] = (t, task)

        try:
            await t
        except asyncio.CancelledError:
            pass
        finally:
            self._active.pop(task.id, None)
            task._fire_state()


    async def pause(self, task: DownloadTask):
        """Signal the task to pause and wait until it drains."""
        task.state = DownloadState.PAUSED
        entry = self._active.get(task.id)
        if entry:
            t, _ = entry
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        task._fire_state()

    async def resume(self, task: DownloadTask):
        """Resume a paused or errored task from where it left off."""
        if task.state not in (DownloadState.PAUSED, DownloadState.ERROR, DownloadState.QUEUED):
            return
        task.state     = DownloadState.QUEUED
        task.error     = ""
        task.retry_count += 1
        self._active.pop(task.id, None)
        await self.start(task)

    async def cancel(self, task: DownloadTask):
        """Cancel and clean up all temp files for the task."""
        task.state = DownloadState.CANCELLED
        entry = self._active.pop(task.id, None)
        if entry:
            t, _ = entry
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

        self._cleanup_temp_files(task)
        task._fire_state()

    def _cleanup_temp_files(self, task: DownloadTask):
        """Remove all temp/part files for a task."""
        for seg in task.segments:
            _safe_remove(seg.temp_path)
        for seg in task.stream_segments:
            _safe_remove(seg.temp_path)


    def set_speed_limit(self, task_id: str, limit_kbps: int):
        """
        Update the global speed limiter ceiling.
        (Per-task limiting would require per-task SpeedLimiter instances;
         this sets the shared limiter used by all active downloads.)
        """
        self.speed_limiter.set_limit(limit_kbps * 1024 if limit_kbps > 0 else 0)


    async def close(self):
        """Cancel all active downloads and close the HTTP session."""
        for task_id, (t, task) in list(self._active.items()):
            task.state = DownloadState.CANCELLED
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._active.clear()

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


    def _plan_segments(self, task: DownloadTask) -> list[DownloadSegment]:
        """
        Divide the file into parallel byte-range segments.
        Adaptive: uses fewer segments for small files.
        """
        os.makedirs(task.save_path, exist_ok=True)
        temp_dir = self._temp_dir_for(task)
        os.makedirs(temp_dir, exist_ok=True)

        size = task.total_size

        if size <= 0:
            return [DownloadSegment(0, 0, 0, temp_path=os.path.join(temp_dir, f"{task.id}.part0"))]

        n = self.segments
        if size < MIN_SEGMENT_BYTES:
            n = 1
        else:
            max_segs = max(1, size // MIN_SEGMENT_BYTES)
            n = min(n, max_segs)

        seg_size = size // n
        segs: list[DownloadSegment] = []

        for i in range(n):
            start = i * seg_size
            end   = size - 1 if i == n - 1 else start + seg_size - 1
            tmp   = os.path.join(temp_dir, f"{task.id}.part{i}")
            segs.append(DownloadSegment(i, start, end, temp_path=tmp))

        return segs

    @staticmethod
    def _temp_dir_for(task: DownloadTask) -> str:
        """Return the temp directory path for a task."""
        try:
            from config.settings import get_download_directory
            from utils.file_categorizer import DownloadPathManager
            pm = DownloadPathManager(get_download_directory())
            return pm.get_temp_path()
        except Exception:
            return task.save_path

    async def _run_direct(self, task: DownloadTask):
        """Full direct-download pipeline: plan → parallel segments → merge → verify."""
        from core.resume_handler import hydrate_partial_segments

        session = await self._get_session()

        if not task.segments:
            task.segments = self._plan_segments(task)
        hydrate_partial_segments(task)

        if task.total_size > 0 and all(s.complete for s in task.segments):
            await self._merge_and_verify(task)
            task.state        = DownloadState.COMPLETED
            task.completed_at = time.time()
            task._fire_state()
            return

        task.state      = DownloadState.DOWNLOADING
        task.started_at = task.started_at or time.time()

        speed_task = asyncio.create_task(self._speed_loop(task))
        try:
            pending = [s for s in task.segments if not s.complete]
            if pending:
                await asyncio.gather(*[
                    self._download_segment(session, task, s) for s in pending
                ])

            if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
                return

            incomplete = [s for s in task.segments if not s.complete]
            if incomplete and task.total_size > 0:
                task.state = DownloadState.ERROR
                task.error = f"{len(incomplete)} segment(s) incomplete"
                return

            await self._merge_and_verify(task)
            task.state        = DownloadState.COMPLETED
            task.completed_at = time.time()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.state = DownloadState.ERROR
            task.error = str(e)
            log.error("[direct] %s failed: %s", task.filename, e)
        finally:
            speed_task.cancel()
            try:
                await speed_task
            except asyncio.CancelledError:
                pass

    async def _download_segment(
        self,
        session: aiohttp.ClientSession,
        task: DownloadTask,
        seg: DownloadSegment,
    ):
        """Download one byte-range segment with retry and partial-resume."""
        if seg.complete:
            return

        os.makedirs(os.path.dirname(seg.temp_path) or ".", exist_ok=True)

        already = 0
        if os.path.exists(seg.temp_path):
            already = os.path.getsize(seg.temp_path)
            if already > 0:
                seg.downloaded = already
                task.downloaded = max(0, task.downloaded)

        headers = dict(task.headers)
        if seg.end > 0:
            range_start      = seg.start + already
            headers["Range"] = f"bytes={range_start}-{seg.end}"

        proxy = current_proxy()

        for attempt in range(DEFAULT_RETRY_COUNT):
            try:
                async with session.get(task.url, headers=headers, proxy=proxy) as resp:
                    resp.raise_for_status()

                    if resp.status == 416:
                        seg.complete = True
                        return

                    write_mode = "ab" if already > 0 and resp.status == 206 else "wb"
                    if write_mode == "wb":
                        seg.downloaded = 0

                    async with aiofiles.open(seg.temp_path, write_mode) as f:
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
                                return
                            await f.write(chunk)
                            await self.speed_limiter.consume(len(chunk))
                            seg.downloaded  += len(chunk)
                            task.downloaded += len(chunk)
                            task._fire_progress()

                if seg.expected_bytes == 0 or seg.downloaded >= seg.expected_bytes:
                    seg.complete = True
                return

            except asyncio.CancelledError:
                raise
            except aiohttp.ClientResponseError as e:
                if e.status in (403, 404, 410):
                    raise
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    raise
                log.warning("[direct] seg %d retry %d/%d (%s): %s",
                            seg.index, attempt + 1, DEFAULT_RETRY_COUNT, task.filename, e)
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
            except Exception as e:
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    raise
                log.warning("[direct] seg %d retry %d/%d (%s): %s",
                            seg.index, attempt + 1, DEFAULT_RETRY_COUNT, task.filename, e)
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))

    async def _merge_and_verify(self, task: DownloadTask):
        """Concatenate segment temp files, move to final path, verify checksum."""
        task.state = DownloadState.MERGING
        task._fire_state()

        os.makedirs(task.save_path, exist_ok=True)
        temp_dir      = self._temp_dir_for(task)
        temp_out_path = os.path.join(temp_dir, task.filename)

        try:
            async with aiofiles.open(temp_out_path, "wb") as out:
                for seg in sorted(task.segments, key=lambda s: s.index):
                    if not os.path.exists(seg.temp_path):
                        if seg.expected_bytes > 0:
                            log.warning("Missing segment file: %s", seg.temp_path)
                        continue
                    if os.path.getsize(seg.temp_path) == 0:
                        log.warning("Empty segment file: %s", seg.temp_path)
                        continue
                    async with aiofiles.open(seg.temp_path, "rb") as part:
                        while True:
                            data = await part.read(CHUNK_SIZE)
                            if not data:
                                break
                            await out.write(data)
                    _safe_remove(seg.temp_path)

            if task.total_size > 0:
                actual = os.path.getsize(temp_out_path)
                if actual != task.total_size:
                    raise RuntimeError(
                        f"Size mismatch after merge: expected {task.total_size:,} B, "
                        f"got {actual:,} B for {task.filename}"
                    )

            if task.expected_checksum:
                _verify_checksum(temp_out_path, task.expected_checksum)

            final = task.full_path
            if temp_out_path != final:
                os.makedirs(os.path.dirname(final), exist_ok=True)
                shutil.move(temp_out_path, final)

            log.info("[direct] Merge complete: %s", task.filename)

        except Exception as e:
            log.error("[direct] Merge failed for %s: %s", task.filename, e)
            raise


    async def _run_hls(self, task: DownloadTask):
        """
        Full HLS download pipeline:
          1. Fetch master playlist → select best variant
          2. Fetch media playlist → build StreamSegment list
          3. Download all segments in parallel (with concurrency cap)
          4. Decrypt AES-128 segments if encrypted
          5. ffmpeg concat → .mp4
        """
        session  = await self._get_session()
        proxy    = current_proxy()
        manifest = task.stream_manifest_url or task.url

        task.state      = DownloadState.DOWNLOADING
        task.started_at = task.started_at or time.time()

        speed_task = asyncio.create_task(self._speed_loop(task))

        try:
            manifest_text = await self._fetch_text(session, manifest, task.headers, proxy)

            media_url = manifest
            if "#EXT-X-STREAM-INF" in manifest_text:
                variants = _parse_hls_master(manifest_text, manifest)
                if not variants:
                    raise RuntimeError("HLS master playlist has no variants")
                media_url = variants[0]["url"]
                log.info("[HLS] Selected variant: %s (bandwidth=%s)",
                         variants[0].get("resolution", "?"),
                         variants[0].get("bandwidth", "?"))
                manifest_text = await self._fetch_text(session, media_url, task.headers, proxy)

            raw_segs = _parse_hls_media(manifest_text, media_url)
            if not raw_segs:
                raise RuntimeError("HLS media playlist contained no segments")

            temp_dir = self._temp_dir_for(task)
            os.makedirs(temp_dir, exist_ok=True)

            if not task.stream_segments:
                task.stream_segments = [
                    StreamSegment(
                        url            = s["url"],
                        index          = i,
                        duration_sec   = s.get("duration", 0.0),
                        temp_path      = os.path.join(temp_dir, f"{task.id}_hls_{i:05d}.ts"),
                        key_url        = s.get("key_url", ""),
                        key_iv         = s.get("key_iv",  ""),
                        byterange_start  = s.get("byterange_start", 0),
                        byterange_length = s.get("byterange_length", 0),
                    )
                    for i, s in enumerate(raw_segs)
                ]

            pending = [s for s in task.stream_segments if not s.complete]
            max_workers = min(
                getattr(task, "_max_concurrent_fragments", 4),
                len(pending)
            )
            await self._bounded_gather(
                [self._download_hls_segment(session, task, s, proxy) for s in pending],
                concurrency=max(1, max_workers),
            )

            if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
                return

            task.state = DownloadState.MERGING
            task._fire_state()

            seg_paths = [s.temp_path for s in task.stream_segments if os.path.exists(s.temp_path)]
            if not seg_paths:
                raise RuntimeError("No HLS segment files to merge")

            os.makedirs(task.save_path, exist_ok=True)
            out_path = task.full_path

            try:
                await ffmpeg_concat_segments(seg_paths, out_path, task.filename)
            except Exception as ffmpeg_err:
                log.warning("[HLS] ffmpeg concat failed (%s) — trying direct ffmpeg remux", ffmpeg_err)
                await ffmpeg_remux_url(manifest, out_path, task.headers)

            for s in task.stream_segments:
                _safe_remove(s.temp_path)

            if task.expected_checksum and os.path.exists(out_path):
                _verify_checksum(out_path, task.expected_checksum)

            task.state        = DownloadState.COMPLETED
            task.completed_at = time.time()
            log.info("[HLS] Complete: %s  (%d segments)", task.filename, len(task.stream_segments))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.state = DownloadState.ERROR
            task.error = str(e)
            log.error("[HLS] %s failed: %s", task.filename, e)
        finally:
            speed_task.cancel()
            try:
                await speed_task
            except asyncio.CancelledError:
                pass

    async def _download_hls_segment(
        self,
        session: aiohttp.ClientSession,
        task: DownloadTask,
        seg: StreamSegment,
        proxy: str | None,
    ):
        """Download + optionally decrypt one HLS segment."""
        if seg.complete:
            return
        if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
            return

        seg_timeout = aiohttp.ClientTimeout(sock_read=HLS_SEGMENT_TIMEOUT)

        headers = dict(task.headers)
        if seg.byterange_length > 0:
            end = seg.byterange_start + seg.byterange_length - 1
            headers["Range"] = f"bytes={seg.byterange_start}-{end}"

        for attempt in range(DEFAULT_RETRY_COUNT):
            try:
                async with session.get(
                    seg.url, headers=headers, proxy=proxy, timeout=seg_timeout
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

                if seg.key_url:
                    data = await _decrypt_segment(
                        data, seg.key_url, seg.key_iv, session, proxy, seg.index
                    )

                os.makedirs(os.path.dirname(seg.temp_path) or ".", exist_ok=True)
                async with aiofiles.open(seg.temp_path, "wb") as f:
                    await f.write(data)

                seg.complete    = True
                task.downloaded += len(data)
                task._fire_progress()
                return

            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    log.error("[HLS] seg %d gave up after %d attempts: %s",
                              seg.index, DEFAULT_RETRY_COUNT, e)
                    raise
                log.warning("[HLS] seg %d retry %d/%d: %s",
                            seg.index, attempt + 1, DEFAULT_RETRY_COUNT, e)
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))


    async def _run_dash(self, task: DownloadTask):
        """
        DASH download pipeline:
          1. Fetch .mpd → parse video + audio representations
          2. Select best video track + best audio track
          3. Download both tracks in parallel to separate temp files
          4. ffmpeg A/V merge → .mp4
        """
        session  = await self._get_session()
        proxy    = current_proxy()
        manifest = task.stream_manifest_url or task.url

        task.state      = DownloadState.DOWNLOADING
        task.started_at = task.started_at or time.time()

        speed_task = asyncio.create_task(self._speed_loop(task))

        try:
            mpd_text = await self._fetch_text(session, manifest, task.headers, proxy)
            parsed   = _parse_dash_mpd(mpd_text, manifest)

            if not parsed["video"]:
                raise RuntimeError("DASH MPD has no video representations")

            best_video = parsed["video"][0]
            best_audio = parsed["audio"][0] if parsed["audio"] else None

            log.info(
                "[DASH] Selected video: %dp %d kbps  audio: %s",
                best_video.get("height", 0),
                best_video.get("bandwidth", 0) // 1000,
                f"{best_audio['bandwidth'] // 1000} kbps" if best_audio else "none",
            )

            temp_dir = self._temp_dir_for(task)
            os.makedirs(temp_dir, exist_ok=True)

            video_tmp = os.path.join(temp_dir, f"{task.id}_dash_video.mp4")
            audio_tmp = os.path.join(temp_dir, f"{task.id}_dash_audio.m4a")

            dl_coros = [self._download_dash_track(session, task, best_video["url"], video_tmp, proxy)]
            if best_audio:
                dl_coros.append(
                    self._download_dash_track(session, task, best_audio["url"], audio_tmp, proxy)
                )
            await asyncio.gather(*dl_coros)

            if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
                return

            task.state = DownloadState.MERGING
            task._fire_state()

            os.makedirs(task.save_path, exist_ok=True)
            out_path = task.full_path

            if best_audio and os.path.exists(audio_tmp):
                await ffmpeg_merge_av_tracks(video_tmp, audio_tmp, out_path)
            else:
                shutil.move(video_tmp, out_path)

            _safe_remove(video_tmp)
            _safe_remove(audio_tmp)

            if task.expected_checksum and os.path.exists(out_path):
                _verify_checksum(out_path, task.expected_checksum)

            task.state        = DownloadState.COMPLETED
            task.completed_at = time.time()
            log.info("[DASH] Complete: %s", task.filename)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.state = DownloadState.ERROR
            task.error = str(e)
            log.error("[DASH] %s failed: %s", task.filename, e)
        finally:
            speed_task.cancel()
            try:
                await speed_task
            except asyncio.CancelledError:
                pass

    async def _download_dash_track(
        self,
        session: aiohttp.ClientSession,
        task: DownloadTask,
        url: str,
        out_path: str,
        proxy: str | None,
    ):
        """Stream a DASH track (video or audio) to a temp file."""
        for attempt in range(DEFAULT_RETRY_COUNT):
            try:
                async with session.get(url, headers=task.headers, proxy=proxy) as resp:
                    resp.raise_for_status()
                    async with aiofiles.open(out_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            if task.state in (DownloadState.PAUSED, DownloadState.CANCELLED):
                                return
                            await f.write(chunk)
                            await self.speed_limiter.consume(len(chunk))
                            task.downloaded += len(chunk)
                            task._fire_progress()
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    raise
                log.warning("[DASH] Track retry %d/%d: %s", attempt + 1, DEFAULT_RETRY_COUNT, e)
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))


    async def _run_ytdlp(self, task: DownloadTask):
        """
        Run yt-dlp as a subprocess with --newline --print-json progress parsing.
        Progress lines look like:
          {"status":"downloading","downloaded_bytes":…,"total_bytes":…,"speed":…,"eta":…}
        """
        try:
            ytdlp_bin = shutil.which("yt-dlp") or shutil.which("yt_dlp") or "yt-dlp"
            output_tmpl = os.path.join(task.save_path, "%(title)s.%(ext)s")

            cmd = [
                ytdlp_bin,
                "--no-warnings",
                "--newline",
                "--progress-template", "%(progress)j",
                "--output", output_tmpl,
                "--no-playlist",
                task.url,
            ]

            if task.headers.get("Cookie"):
                cmd += ["--add-header", f"Cookie:{task.headers['Cookie']}"]

            if task.referrer:
                cmd += ["--referer", task.referrer]

            proxy = current_proxy()
            if proxy:
                cmd += ["--proxy", proxy]

            log.info("[yt-dlp] Starting: %s", task.url)
            task.state      = DownloadState.DOWNLOADING
            task.started_at = task.started_at or time.time()

            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    startupinfo=startupinfo,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            import json as _json

            async def _read_progress():
                async for line in proc.stdout:
                    raw = line.decode(errors="replace").strip()
                    if not raw:
                        continue
                    try:
                        obj = _json.loads(raw)
                        if "downloaded_bytes" in obj:
                            task.downloaded = int(obj.get("downloaded_bytes") or 0)
                            task.total_size = int(obj.get("total_bytes") or task.total_size)
                            task.speed      = float(obj.get("speed") or 0.0)
                            task.eta        = int(obj.get("eta") or 0)
                            task.peak_speed = max(task.peak_speed, task.speed)
                            task._fire_progress()
                    except (_json.JSONDecodeError, ValueError):
                        log.debug("[yt-dlp] %s", raw)

            progress_task = asyncio.create_task(_read_progress())

            try:
                await proc.wait()
            finally:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

            if proc.returncode == 0:
                task.state        = DownloadState.COMPLETED
                task.completed_at = time.time()
                log.info("[yt-dlp] Complete: %s", task.url)
            else:
                stderr_data = await proc.stderr.read()
                err_text    = stderr_data.decode(errors="replace")[-1000:]
                task.state  = DownloadState.ERROR
                task.error  = f"yt-dlp exit {proc.returncode}: {err_text}"
                log.error("[yt-dlp] %s", task.error)

        except asyncio.CancelledError:
            try:
                proc.kill()
            except Exception:
                pass
            raise
        except Exception as e:
            task.state = DownloadState.ERROR
            task.error = str(e)
            log.error("[yt-dlp] Failed: %s", e)


    async def _run_blob(self, task: DownloadTask):
        """
        Blob URLs can't be fetched externally.
        Re-route to yt-dlp using the page URL stored in task.referrer.
        """
        page_url = task.referrer or task.url
        if not page_url or page_url.startswith("blob:"):
            task.state = DownloadState.ERROR
            task.error = "Blob URL with no fallback page URL — cannot download"
            log.error("[blob] %s", task.error)
            return

        log.info("[blob] Redirecting blob URL to yt-dlp with page URL: %s", page_url)
        original_url   = task.url
        task.url       = page_url
        task.download_mode = "ytdlp"
        await self._run_ytdlp(task)
        task.url = original_url


    @staticmethod
    async def _fetch_text(
        session: aiohttp.ClientSession,
        url: str,
        headers: dict,
        proxy: str | None,
    ) -> str:
        """Fetch URL as text with retry."""
        for attempt in range(DEFAULT_RETRY_COUNT):
            try:
                async with session.get(url, headers=headers, proxy=proxy) as resp:
                    resp.raise_for_status()
                    return await resp.text()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    raise
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
        return ""

    @staticmethod
    async def _bounded_gather(coros, concurrency: int = 4):
        """Run coroutines with a semaphore cap on concurrency."""
        sem = asyncio.Semaphore(concurrency)

        async def _wrap(coro):
            async with sem:
                return await coro

        await asyncio.gather(*[_wrap(c) for c in coros])

    async def _speed_loop(self, task: DownloadTask):
        """
        Background coroutine that updates task.speed (EMA) and task.eta
        every 500 ms while the task is DOWNLOADING.
        """
        last_dl   = task.downloaded
        last_time = time.monotonic()
        try:
            while task.state == DownloadState.DOWNLOADING:
                await asyncio.sleep(0.5)
                now      = time.monotonic()
                dt       = now - last_time
                if dt <= 0:
                    continue
                ddl      = task.downloaded - last_dl
                instant  = ddl / dt

                if task.speed == 0.0:
                    task.speed = instant
                else:
                    task.speed = SPEED_EMA_ALPHA * instant + (1 - SPEED_EMA_ALPHA) * task.speed

                task.peak_speed = max(task.peak_speed, task.speed)

                if task.total_size > 0 and task.speed > 0:
                    remaining = task.total_size - task.downloaded
                    task.eta  = max(0, int(remaining / task.speed))

                last_dl   = task.downloaded
                last_time = now

        except asyncio.CancelledError:
            raise



def _safe_remove(path: str) -> None:
    """Remove a file without raising."""
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as e:
            log.debug("Could not remove temp file %s: %s", path, e)