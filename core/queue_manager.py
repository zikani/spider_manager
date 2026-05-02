"""
Spider Manager - Queue Manager
Manages the global download queue with priority scheduling and concurrency control.
"""

import asyncio
import uuid
import json
from pathlib import Path
from collections import deque
from collections.abc import Callable
from typing import Optional

from config.constants import DEFAULT_CONCURRENT, DownloadState
from core.download_engine import DownloadEngine, DownloadTask
from utils.logger import get_logger

log = get_logger(__name__)


class QueueManager:
    """
    Central download queue with:
    - Priority queuing (high/normal/low)
    - Configurable concurrency limit
    - Category-based filtering
    """

    def __init__(
        self,
        engine: DownloadEngine,
        max_concurrent: int = DEFAULT_CONCURRENT,
        scheduler_allows_dispatch: Callable[[], bool] | None = None,
    ):
        self.engine = engine
        self.max_concurrent = max_concurrent
        self._scheduler_allows_dispatch = scheduler_allows_dispatch or (lambda: True)
        self._queue: deque[DownloadTask] = deque()
        self._active: dict[str, DownloadTask] = {}
        self._completed: list[DownloadTask] = []
        self._lock = asyncio.Lock()
        self._load_queue()

    def _load_queue(self):
        """Internal helper to load queue from disk."""
        config_path = Path.home() / ".spider_manager" / "queue.json"
        if not config_path.exists():
            return
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            for d in data.get("queue", []):
                self._queue.append(self._dict_to_task(d))
            for d in data.get("active", []):
                t = self._dict_to_task(d)
                t.state = DownloadState.PAUSED
                self._queue.append(t)
            for d in data.get("completed", []):
                self._completed.append(self._dict_to_task(d))
        except Exception as e:
            log.warning("Failed to load queue from %s: %s", config_path, e)

    def save_queue(self):
        """Save the current queue to a JSON file."""
        data = {
            "queue": [self._task_to_dict(t) for t in self._queue],
            "active": [self._task_to_dict(t) for t in self._active.values()],
            "completed": [self._task_to_dict(t) for t in self._completed]
        }
        config_dir = Path.home() / ".spider_manager"
        config_dir.mkdir(exist_ok=True)
        with open(config_dir / "queue.json", "w") as f:
            json.dump(data, f, indent=4)

    def _task_to_dict(self, task: DownloadTask):
        from core.download_engine import DownloadSegment
        return {
            "id": task.id,
            "url": task.url,
            "filename": task.filename,
            "save_path": task.save_path,
            "total_size": task.total_size,
            "downloaded": task.downloaded,
            "state": task.state,
            "category": task.category,
            "segments": [
                {
                    "index": s.index,
                    "start": s.start,
                    "end": s.end,
                    "downloaded": s.downloaded,
                    "temp_path": s.temp_path,
                    "complete": s.complete
                } for s in task.segments
            ]
        }

    def _dict_to_task(self, d: dict):
        from core.download_engine import DownloadSegment
        task = DownloadTask(
            id=d["id"],
            url=d["url"],
            filename=d["filename"],
            save_path=d["save_path"],
            total_size=d["total_size"],
            downloaded=d["downloaded"],
            state=d["state"],
            category=d.get("category", "Other")
        )
        task.segments = [
            DownloadSegment(
                index=s["index"],
                start=s["start"],
                end=s["end"],
                downloaded=s["downloaded"],
                temp_path=s["temp_path"],
                complete=s["complete"]
            ) for s in d.get("segments", [])
        ]
        return task

    def set_max_concurrent(self, n: int) -> None:
        self.max_concurrent = max(1, min(10, n))

    @property
    def all_tasks(self) -> list[DownloadTask]:
        return list(self._queue) + list(self._active.values()) + self._completed

    def tasks_snapshot(self) -> list[DownloadTask]:
        """Stable ordering: queue order, then active, then completed (recent last)."""
        return list(self._queue) + list(self._active.values()) + list(self._completed)

    def create_task(
        self,
        url: str,
        filename: str,
        save_path: str,
        category: str = "Other",
        referrer: str = "",
        headers: dict | None = None,
    ) -> DownloadTask:
        return DownloadTask(
            id=str(uuid.uuid4()),
            url=url,
            filename=filename,
            save_path=save_path,
            category=category,
            referrer=referrer,
            headers=headers or {},
        )

    async def add(self, task: DownloadTask) -> str:
        async with self._lock:
            self._queue.append(task)
        await self._try_dispatch()
        return task.id

    async def pause(self, task_id: str):
        task = self._active.get(task_id)
        if task:
            await self.engine.pause(task)
            async with self._lock:
                if task_id in self._active:
                    del self._active[task_id]
                    self._queue.appendleft(task)

    async def resume(self, task_id: str):
        task = self._find(task_id)
        if not task or task.state != DownloadState.PAUSED:
            return
        task.state = DownloadState.QUEUED
        async with self._lock:
            self._queue = deque(t for t in self._queue if t.id != task_id)
            if task_id in self._active:
                del self._active[task_id]
            self._queue.appendleft(task)
        await self._try_dispatch()

    async def cancel(self, task_id: str):
        task = self._find(task_id)
        if not task:
            return
        was_active = task_id in self._active
        await self.engine.cancel(task)
        async with self._lock:
            self._active.pop(task_id, None)
            self._queue = deque(t for t in self._queue if t.id != task_id)
            if not was_active:
                self._completed.append(task)

    def remove(self, task_id: str):
        if self._find(task_id):
            self._completed = [t for t in self._completed if t.id != task_id]
            self._queue = deque(t for t in self._queue if t.id != task_id)

    def _find(self, task_id: str) -> Optional[DownloadTask]:
        if task_id in self._active:
            return self._active[task_id]
        for t in self._queue:
            if t.id == task_id:
                return t
        for t in self._completed:
            if t.id == task_id:
                return t
        return None

    async def wake_dispatch(self) -> None:
        """Retry dispatch (e.g. when download schedule window opens)."""
        await self._try_dispatch()

    async def _try_dispatch(self):
        async with self._lock:
            while (
                self._queue
                and len(self._active) < self.max_concurrent
                and self._scheduler_allows_dispatch()
            ):
                task = self._queue.popleft()
                self._active[task.id] = task
                asyncio.create_task(self._run_task(task))

    async def _run_task(self, task: DownloadTask):
        try:
            await self.engine.start(task)
        finally:
            async with self._lock:
                if task.id in self._active:
                    del self._active[task.id]
                terminal = task.state in (
                    DownloadState.COMPLETED,
                    DownloadState.ERROR,
                    DownloadState.CANCELLED,
                )
                if terminal:
                    self._completed.append(task)
            await self._try_dispatch()

    async def resume_all(self):
        """Resume all paused downloads."""
        async with self._lock:
            paused_tasks = [t for t in self._queue if t.state == DownloadState.PAUSED]
            for task in paused_tasks:
                task.state = DownloadState.QUEUED
                self._queue = deque(t for t in self._queue if t.id != task.id)
                self._queue.appendleft(task)
        await self._try_dispatch()

    async def pause_all(self):
        """Pause all active downloads."""
        active_tasks = list(self._active.values())
        for task in active_tasks:
            await self.pause(task.id)

    async def clear_all(self):
        """Clear all tasks from queue, active, and completed lists."""
        async with self._lock:
            self._queue.clear()
            self._active.clear()
            self._completed.clear()

    async def move_to_top(self, task_id: str):
        """Move task to top of queue."""
        async with self._lock:
            task = self._find(task_id)
            if task and task in self._queue:
                self._queue.remove(task)
                self._queue.appendleft(task)

    async def move_up(self, task_id: str):
        """Move task up in queue."""
        async with self._lock:
            task = self._find(task_id)
            if task and task in self._queue:
                idx = list(self._queue).index(task)
                if idx > 0:
                    queue_list = list(self._queue)
                    queue_list[idx], queue_list[idx-1] = queue_list[idx-1], queue_list[idx]
                    self._queue = deque(queue_list)

    async def move_down(self, task_id: str):
        """Move task down in queue."""
        async with self._lock:
            task = self._find(task_id)
            if task and task in self._queue:
                queue_list = list(self._queue)
                idx = queue_list.index(task)
                if idx < len(queue_list) - 1:
                    queue_list[idx], queue_list[idx+1] = queue_list[idx+1], queue_list[idx]
                    self._queue = deque(queue_list)

    async def move_to_bottom(self, task_id: str):
        """Move task to bottom of queue."""
        async with self._lock:
            task = self._find(task_id)
            if task and task in self._queue:
                self._queue.remove(task)
                self._queue.append(task)

    async def shuffle(self):
        """Shuffle the queue order."""
        import random
        async with self._lock:
            queue_list = list(self._queue)
            random.shuffle(queue_list)
            self._queue = deque(queue_list)

    async def restart_failed(self):
        """Restart all failed downloads."""
        async with self._lock:
            for task in self._completed:
                if task.state == DownloadState.ERROR:
                    task.state = DownloadState.QUEUED
                    task.error = ""
                    task.retry_count = 0
                    self._queue.append(task)
            self._completed = [t for t in self._completed if t.state != DownloadState.ERROR]
        await self._try_dispatch()

    async def force_check_all(self):
        """Force check all URLs."""
        for task in self.all_tasks:
            if task.url:
                # TODO: Implement URL validation
                pass


    def get_stats(self) -> dict:
        active = list(self._active.values())
        total_speed = sum(t.speed for t in active)
        paused = sum(1 for t in self._queue if t.state == DownloadState.PAUSED)
        downloading = len(active)
        completed = len([t for t in self._completed if t.state == DownloadState.COMPLETED])
        failed = len([t for t in self._completed if t.state == DownloadState.ERROR])
        return {
            "queued": len(self._queue),
            "active": downloading,
            "paused": paused,
            "completed": completed,
            "failed": failed,
            "total_speed": total_speed,
        }
