import asyncio
from unittest.mock import AsyncMock

from config.constants import DownloadState
from core.download_engine import DownloadEngine, DownloadTask
from core.queue_manager import QueueManager


def test_dispatch_runs_engine(tmp_path):
    async def _run():
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()

        q = QueueManager(engine, max_concurrent=2)
        t = q.create_task("http://x", "a.bin", str(tmp_path), category="Other")

        await q.add(t)
        await asyncio.sleep(0.05)
        engine.start.assert_awaited()
        await engine.close()

    asyncio.run(_run())


def test_resume_requeues_paused(tmp_path):
    async def _run():
        engine = DownloadEngine(segments=1)
        calls = []

        async def fake_start(task: DownloadTask):
            calls.append(task.id)
            task.state = DownloadState.COMPLETED

        engine.start = fake_start

        q = QueueManager(engine, max_concurrent=1)
        t = q.create_task("http://x", "a.bin", str(tmp_path))
        t.state = DownloadState.PAUSED
        async with q._lock:
            q._queue.append(t)

        await q.resume(t.id)
        await asyncio.sleep(0.05)
        assert calls == [t.id]
        await engine.close()

    asyncio.run(_run())
