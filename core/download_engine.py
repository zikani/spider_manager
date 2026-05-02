"""
Spider Manager - Download Engine
Core multi-threaded, segmented download engine using asyncio + aiohttp.
"""

import asyncio
import aiohttp
import aiofiles
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from config.constants import (
    DEFAULT_SEGMENTS,
    DEFAULT_RETRY_COUNT,
    RETRY_DELAY,
    CONNECTION_TIMEOUT,
    READ_TIMEOUT,
    DownloadState,
)
from core.speed_limiter import SpeedLimiter
from utils.file_utils import sanitize_filename
from utils.logger import get_logger
from utils.network_utils import current_proxy
from utils.url_parser import extract_filename

log = get_logger(__name__)


@dataclass
class DownloadSegment:
    """Represents a single byte-range segment of a download."""

    index: int
    start: int
    end: int
    downloaded: int = 0
    temp_path: str = ""
    complete: bool = False


@dataclass
class DownloadTask:
    """Represents a download job with all metadata."""

    id: str
    url: str
    filename: str
    save_path: str
    total_size: int = 0
    downloaded: int = 0
    segments: list[DownloadSegment] = field(default_factory=list)
    state: str = DownloadState.QUEUED
    speed: float = 0.0  # bytes/sec
    eta: int = 0  # seconds
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    category: str = "Other"
    referrer: str = ""
    headers: dict = field(default_factory=dict)
    progress_callback: Optional[Callable] = None
    state_callback: Optional[Callable] = None

    @property
    def progress(self) -> float:
        if self.total_size == 0:
            return 0.0
        return min(self.downloaded / self.total_size * 100, 100.0)

    @property
    def full_path(self) -> str:
        return os.path.join(self.save_path, self.filename)


class DownloadEngine:
    """
    Multi-segment async download engine.
    - Splits files into N byte-range segments for parallel download
    - Supports resume via partial files
    - Retry logic with exponential backoff
    - Real-time speed and ETA calculation
    """

    def __init__(
        self,
        segments: int = DEFAULT_SEGMENTS,
        speed_limiter: SpeedLimiter | None = None,
    ):
        self.segments = segments
        self.speed_limiter = speed_limiter or SpeedLimiter()
        self._run_tasks: dict[str, asyncio.Task] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=100)
            timeout = aiohttp.ClientTimeout(
                connect=CONNECTION_TIMEOUT,
                sock_read=READ_TIMEOUT,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Spider-Manager/1.0"},
            )
        return self._session

    async def probe(self, url: str, headers: dict | None = None) -> dict:
        """
        HEAD request to get file metadata.
        Returns: {size, filename, resumable, content_type}
        """
        session = await self._get_session()
        h = headers or {}
        proxy = current_proxy()
        async with session.head(url, headers=h, allow_redirects=True, proxy=proxy) as resp:
            resp.raise_for_status()
            size = int(resp.headers.get("Content-Length", 0))
            resumable = "bytes" in resp.headers.get("Accept-Ranges", "")
            raw_filename = extract_filename(str(resp.url), dict(resp.headers))
            filename = sanitize_filename(raw_filename)
            return {
                "size": size,
                "filename": filename,
                "resumable": resumable,
                "content_type": resp.headers.get("Content-Type", ""),
                "url": str(resp.url),
            }

    def _plan_segments(self, task: DownloadTask) -> list[DownloadSegment]:
        """Divide file into segments based on size."""
        size = task.total_size
        n = self.segments if size > 0 else 1
        if size > 0:
            chunk = size // n
            segs = []
            for i in range(n):
                start = i * chunk
                end = (start + chunk - 1) if i < n - 1 else size - 1
                tmp = f"{task.full_path}.part{i}"
                segs.append(DownloadSegment(i, start, end, temp_path=tmp))
            return segs
        return [DownloadSegment(0, 0, 0, temp_path=f"{task.full_path}.part0")]

    async def _download_segment(
        self,
        session: aiohttp.ClientSession,
        task: DownloadTask,
        seg: DownloadSegment,
    ):
        """Download a single byte-range segment with retry."""
        if seg.complete:
            return
        headers = dict(task.headers)
        if seg.end > 0:
            headers["Range"] = f"bytes={seg.start + seg.downloaded}-{seg.end}"

        proxy = current_proxy()
        for attempt in range(DEFAULT_RETRY_COUNT):
            try:
                async with session.get(task.url, headers=headers, proxy=proxy) as resp:
                    resp.raise_for_status()
                    mode = "ab" if seg.downloaded > 0 else "wb"
                    async with aiofiles.open(seg.temp_path, mode) as f:
                        async for chunk in resp.content.iter_chunked(65536):
                            if task.state == DownloadState.PAUSED:
                                return
                            await f.write(chunk)
                            await self.speed_limiter.consume(len(chunk))
                            seg.downloaded += len(chunk)
                            task.downloaded += len(chunk)
                            if task.progress_callback:
                                task.progress_callback(task)
                seg.complete = True
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == DEFAULT_RETRY_COUNT - 1:
                    log.error(
                        "Segment %d for %s gave up after %d attempts: %s",
                        seg.index, task.filename, DEFAULT_RETRY_COUNT, e,
                    )
                    raise
                log.warning(
                    "Segment %d for %s retry %d/%d: %s",
                    seg.index, task.filename, attempt + 1, DEFAULT_RETRY_COUNT, e,
                )
                await asyncio.sleep(RETRY_DELAY * (2**attempt))

    async def _merge_segments(self, task: DownloadTask):
        """Concatenate all segment temp files into the final file."""
        if task.state == DownloadState.CANCELLED:
            return
        task.state = DownloadState.MERGING
        if task.state_callback:
            task.state_callback(task)
        async with aiofiles.open(task.full_path, "wb") as out:
            for seg in sorted(task.segments, key=lambda s: s.index):
                async with aiofiles.open(seg.temp_path, "rb") as part:
                    while True:
                        data = await part.read(65536)
                        if not data:
                            break
                        await out.write(data)
                os.remove(seg.temp_path)

    async def _run_download(self, task: DownloadTask):
        from core.resume_handler import hydrate_partial_segments

        session = await self._get_session()
        if not task.segments:
            task.segments = self._plan_segments(task)
        hydrate_partial_segments(task)

        if task.total_size > 0 and all(s.complete for s in task.segments):
            await self._merge_segments(task)
            task.state = DownloadState.COMPLETED
            task.completed_at = time.time()
            if task.state_callback:
                task.state_callback(task)
            return

        task.state = DownloadState.DOWNLOADING
        if task.started_at is None:
            task.started_at = time.time()

        speed_tracker = {"last_dl": task.downloaded, "last_time": time.time()}

        async def update_speed():
            try:
                while task.state == DownloadState.DOWNLOADING:
                    await asyncio.sleep(0.5)
                    now = time.time()
                    dt = now - speed_tracker["last_time"]
                    ddl = task.downloaded - speed_tracker["last_dl"]
                    task.speed = ddl / dt if dt > 0 else 0
                    remaining = task.total_size - task.downloaded
                    task.eta = int(remaining / task.speed) if task.speed > 0 else 0
                    speed_tracker["last_dl"] = task.downloaded
                    speed_tracker["last_time"] = now
            except asyncio.CancelledError:
                raise

        speed_task = asyncio.create_task(update_speed())
        try:
            pending = [s for s in task.segments if not s.complete]
            if pending:
                await asyncio.gather(
                    *[self._download_segment(session, task, s) for s in pending]
                )
            if task.state == DownloadState.PAUSED:
                return
            if task.state == DownloadState.CANCELLED:
                return
            if not all(s.complete for s in task.segments):
                if task.total_size > 0:
                    task.state = DownloadState.ERROR
                    task.error = "Incomplete download"
                else:
                    await self._merge_segments(task)
                    task.state = DownloadState.COMPLETED
                    task.completed_at = time.time()
            else:
                await self._merge_segments(task)
                task.state = DownloadState.COMPLETED
                task.completed_at = time.time()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.state = DownloadState.ERROR
            task.error = str(e)
        finally:
            speed_task.cancel()
            try:
                await speed_task
            except asyncio.CancelledError:
                pass
            if task.state_callback:
                task.state_callback(task)

    async def start(self, task: DownloadTask):
        """Begin or resume downloading a task."""
        t = asyncio.create_task(self._run_download(task))
        self._run_tasks[task.id] = t
        try:
            await t
        except asyncio.CancelledError:
            pass
        finally:
            self._run_tasks.pop(task.id, None)

    async def pause(self, task: DownloadTask):
        task.state = DownloadState.PAUSED
        rt = self._run_tasks.get(task.id)
        if rt:
            rt.cancel()
            try:
                await rt
            except asyncio.CancelledError:
                pass

    async def resume(self, task: DownloadTask):
        await self.start(task)

    async def cancel(self, task: DownloadTask):
        task.state = DownloadState.CANCELLED
        rt = self._run_tasks.pop(task.id, None)
        if rt:
            rt.cancel()
            try:
                await rt
            except asyncio.CancelledError:
                pass
        for seg in task.segments:
            if seg.temp_path and os.path.exists(seg.temp_path):
                try:
                    os.remove(seg.temp_path)
                except OSError:
                    pass

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
