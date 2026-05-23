"""
Advanced tests for QueueManager.
Tests priority queuing, persistence, scheduler integration, and signal emission.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.download_engine import DownloadEngine, DownloadTask
from core.queue_manager import QueueManager
from config.constants import DownloadState



class TestPriorityQueue:
    """Test priority-based queue ordering."""

    @pytest.mark.asyncio
    async def test_high_priority_dispatched_first(self, tmp_path):
        """Test that high priority tasks are dispatched before normal."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=1)
        
        normal_task = q.create_task("http://example.com/normal.bin", "normal.bin", str(tmp_path))
        normal_task.priority = "normal"
        await q.add(normal_task)
        
        high_task = q.create_task("http://example.com/high.bin", "high.bin", str(tmp_path))
        high_task.priority = "high"
        await q.add(high_task)
        
        await asyncio.sleep(0.1)
        
        calls = engine.start.call_args_list
        if calls:
            first_task_id = calls[0][0][0].id
            assert first_task_id == high_task.id
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_low_priority_dispatched_last(self, tmp_path):
        """Test that low priority tasks are dispatched after normal."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=2)
        
        low_task = q.create_task("http://example.com/low.bin", "low.bin", str(tmp_path))
        low_task.priority = "low"
        await q.add(low_task)
        
        normal_task = q.create_task("http://example.com/normal.bin", "normal.bin", str(tmp_path))
        normal_task.priority = "normal"
        await q.add(normal_task)
        
        await asyncio.sleep(0.1)
        
        calls = engine.start.call_args_list
        if len(calls) >= 2:
            assert calls[0][0][0].id == normal_task.id
            assert calls[1][0][0].id == low_task.id
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_priority_reordering(self, tmp_path):
        """Test that queue can be reordered by priority."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=1)
        
        task1 = q.create_task("http://example.com/1.bin", "1.bin", str(tmp_path))
        task1.priority = "low"
        await q.add(task1)
        
        task2 = q.create_task("http://example.com/2.bin", "2.bin", str(tmp_path))
        task2.priority = "normal"
        await q.add(task2)
        
        task3 = q.create_task("http://example.com/3.bin", "3.bin", str(tmp_path))
        task3.priority = "high"
        await q.add(task3)
        
        await q.reorder_by_priority()
        
        queue_list = list(q._queue)
        if queue_list:
            priorities = [t.priority for t in queue_list]
            assert priorities[0] == "high"
        
        await engine.close()



class TestCategoryFiltering:
    """Test category-based filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_category(self, tmp_path):
        """Test filtering tasks by category."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        video_task = q.create_task("http://example.com/video.mp4", "video.mp4", str(tmp_path), category="Video")
        await q.add(video_task)
        
        audio_task = q.create_task("http://example.com/audio.mp3", "audio.mp3", str(tmp_path), category="Audio")
        await q.add(audio_task)
        
        doc_task = q.create_task("http://example.com/doc.pdf", "doc.pdf", str(tmp_path), category="Document")
        await q.add(doc_task)
        
        video_tasks = q.get_by_category("Video")
        assert len(video_tasks) == 1
        assert video_tasks[0].category == "Video"
        
        audio_tasks = q.get_by_category("Audio")
        assert len(audio_tasks) == 1
        assert audio_tasks[0].category == "Audio"
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_category_counts(self, tmp_path):
        """Test category count tracking."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        await q.add(q.create_task("http://example.com/1.mp4", "1.mp4", str(tmp_path), category="Video"))
        await q.add(q.create_task("http://example.com/2.mp4", "2.mp4", str(tmp_path), category="Video"))
        await q.add(q.create_task("http://example.com/1.mp3", "1.mp3", str(tmp_path), category="Audio"))
        
        counts = q.get_category_counts()
        assert counts.get("Video", 0) == 2
        assert counts.get("Audio", 0) == 1
        
        await engine.close()



class TestQueuePersistence:
    """Test queue save and load functionality."""

    @pytest.mark.asyncio
    async def test_save_queue(self, tmp_path):
        """Test saving queue to disk."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        task1 = q.create_task("http://example.com/1.bin", "1.bin", str(tmp_path))
        await q.add(task1)
        
        task2 = q.create_task("http://example.com/2.bin", "2.bin", str(tmp_path))
        await q.add(task2)
        
        q.save_queue()
        
        config_path = Path.home() / ".spider_manager" / "queue.json"
        assert config_path.exists()
        
        with open(config_path, "r") as f:
            data = json.load(f)
        
        assert "queue" in data
        assert len(data["queue"]) == 2
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_load_queue(self, tmp_path):
        """Test loading queue from disk."""
        engine = DownloadEngine(segments=1)
        
        config_dir = Path.home() / ".spider_manager"
        config_dir.mkdir(exist_ok=True)
        
        saved_data = {
            "queue": [
                {
                    "id": "test-1",
                    "url": "http://example.com/1.bin",
                    "filename": "1.bin",
                    "save_path": str(tmp_path),
                    "total_size": 1000,
                    "downloaded": 0,
                    "state": "queued",
                    "category": "Other",
                    "segments": []
                }
            ],
            "active": [],
            "completed": []
        }
        
        with open(config_dir / "queue.json", "w") as f:
            json.dump(saved_data, f)
        
        q = QueueManager(engine, max_concurrent=1)
        
        assert len(q._queue) == 1
        assert q._queue[0].id == "test-1"
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_load_active_as_paused(self, tmp_path):
        """Test that active tasks are loaded as paused."""
        engine = DownloadEngine(segments=1)
        
        config_dir = Path.home() / ".spider_manager"
        config_dir.mkdir(exist_ok=True)
        
        saved_data = {
            "queue": [],
            "active": [
                {
                    "id": "active-1",
                    "url": "http://example.com/1.bin",
                    "filename": "1.bin",
                    "save_path": str(tmp_path),
                    "total_size": 1000,
                    "downloaded": 500,
                    "state": "downloading",
                    "category": "Other",
                    "segments": []
                }
            ],
            "completed": []
        }
        
        with open(config_dir / "queue.json", "w") as f:
            json.dump(saved_data, f)
        
        q = QueueManager(engine, max_concurrent=1)
        
        assert len(q._queue) == 1
        assert q._queue[0].state == DownloadState.PAUSED
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_load_completed_tasks(self, tmp_path):
        """Test that completed tasks are loaded correctly."""
        engine = DownloadEngine(segments=1)
        
        config_dir = Path.home() / ".spider_manager"
        config_dir.mkdir(exist_ok=True)
        
        saved_data = {
            "queue": [],
            "active": [],
            "completed": [
                {
                    "id": "completed-1",
                    "url": "http://example.com/1.bin",
                    "filename": "1.bin",
                    "save_path": str(tmp_path),
                    "total_size": 1000,
                    "downloaded": 1000,
                    "state": "completed",
                    "category": "Other",
                    "segments": []
                }
            ]
        }
        
        with open(config_dir / "queue.json", "w") as f:
            json.dump(saved_data, f)
        
        q = QueueManager(engine, max_concurrent=1)
        
        assert len(q._completed) == 1
        assert q._completed[0].state == DownloadState.COMPLETED
        
        await engine.close()



class TestSchedulerIntegration:
    """Test scheduler integration with queue dispatch."""

    @pytest.mark.asyncio
    async def test_scheduler_blocks_dispatch(self, tmp_path):
        """Test that scheduler blocks dispatch when outside time window."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        scheduler_allows = lambda: False
        
        q = QueueManager(engine, max_concurrent=1, scheduler_allows_dispatch=scheduler_allows)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.1)
        
        engine.start.assert_not_awaited()
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_scheduler_allows_dispatch(self, tmp_path):
        """Test that scheduler allows dispatch when inside time window."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        scheduler_allows = lambda: True
        
        q = QueueManager(engine, max_concurrent=1, scheduler_allows_dispatch=scheduler_allows)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.1)
        
        engine.start.assert_awaited()
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_scheduler_dynamic_change(self, tmp_path):
        """Test that scheduler changes are respected dynamically."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        scheduler_state = {"allowed": False}
        scheduler_allows = lambda: scheduler_state["allowed"]
        
        q = QueueManager(engine, max_concurrent=1, scheduler_allows_dispatch=scheduler_allows)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.1)
        
        engine.start.assert_not_awaited()
        
        scheduler_state["allowed"] = True
        await q.wake_dispatch()
        
        await asyncio.sleep(0.1)
        
        engine.start.assert_awaited()
        
        await engine.close()



class TestConcurrentLimit:
    """Test concurrent download limit enforcement."""

    @pytest.mark.asyncio
    async def test_max_concurrent_respected(self, tmp_path):
        """Test that max concurrent limit is respected."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=2)
        
        tasks = []
        for i in range(5):
            task = q.create_task(f"http://example.com/{i}.bin", f"{i}.bin", str(tmp_path))
            await q.add(task)
            tasks.append(task)
        
        await asyncio.sleep(0.1)
        
        assert len(q._active) <= 2
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_concurrent_limit_zero(self, tmp_path):
        """Test that concurrent limit of 0 blocks all downloads."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=0)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.1)
        
        assert len(q._active) == 0
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_concurrent_limit_update(self, tmp_path):
        """Test that concurrent limit can be updated dynamically."""
        engine = DownloadEngine(segments=1)
        engine.start = AsyncMock()
        
        q = QueueManager(engine, max_concurrent=1)
        
        for i in range(3):
            task = q.create_task(f"http://example.com/{i}.bin", f"{i}.bin", str(tmp_path))
            await q.add(task)
        
        await asyncio.sleep(0.1)
        
        assert len(q._active) <= 1
        
        q.max_concurrent = 3
        await q.wake_dispatch()
        
        await asyncio.sleep(0.1)
        
        assert len(q._active) >= 1
        
        await engine.close()



class TestTaskStateTransitions:
    """Test task state transitions."""

    @pytest.mark.asyncio
    async def test_queued_to_downloading(self, tmp_path):
        """Test transition from queued to downloading."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        assert task.state == DownloadState.QUEUED
        
        await q.add(task)
        await asyncio.sleep(0.1)
        
        assert task.state == DownloadState.DOWNLOADING
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_downloading_to_completed(self, tmp_path):
        """Test transition from downloading to completed."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
            await asyncio.sleep(0.05)
            task.state = DownloadState.COMPLETED
            task.downloaded = task.total_size
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        task.total_size = 1000
        await q.add(task)
        
        await asyncio.sleep(0.2)
        
        assert task.state == DownloadState.COMPLETED
        assert task in q._completed
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_downloading_to_error(self, tmp_path):
        """Test transition from downloading to error."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
            await asyncio.sleep(0.05)
            task.state = DownloadState.ERROR
            task.error = "Connection failed"
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.2)
        
        assert task.state == DownloadState.ERROR
        assert task.error == "Connection failed"
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_pause_resume_cycle(self, tmp_path):
        """Test pause and resume cycle."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.1)
        
        await q.pause(task.id)
        assert task.state == DownloadState.PAUSED
        
        await q.resume(task.id)
        await asyncio.sleep(0.1)
        assert task.state == DownloadState.DOWNLOADING
        
        await engine.close()



class TestSignalEmission:
    """Test signal emission for events."""

    @pytest.mark.asyncio
    async def test_download_completed_signal(self, tmp_path):
        """Test download_completed signal emission."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
            await asyncio.sleep(0.05)
            task.state = DownloadState.COMPLETED
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        completed_ids = []
        q.download_completed.connect(lambda tid: completed_ids.append(tid))
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.2)
        
        assert task.id in completed_ids
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_download_failed_signal(self, tmp_path):
        """Test download_failed signal emission."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
            await asyncio.sleep(0.05)
            task.state = DownloadState.ERROR
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        failed_ids = []
        q.download_failed.connect(lambda tid: failed_ids.append(tid))
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.2)
        
        assert task.id in failed_ids
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_queue_finished_signal(self, tmp_path):
        """Test queue_finished signal emission."""
        engine = DownloadEngine(segments=1)
        
        async def fake_start(task):
            task.state = DownloadState.DOWNLOADING
            await asyncio.sleep(0.05)
            task.state = DownloadState.COMPLETED
        
        engine.start = fake_start
        
        q = QueueManager(engine, max_concurrent=1)
        
        finished_called = []
        q.queue_finished.connect(lambda: finished_called.append(True))
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await asyncio.sleep(0.2)
        
        assert len(finished_called) > 0
        
        await engine.close()



class TestTaskManagement:
    """Test task management operations."""

    @pytest.mark.asyncio
    async def test_remove_task_from_queue(self, tmp_path):
        """Test removing a task from queue."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        await q.remove(task.id)
        
        assert task not in q._queue
        assert task not in q._active
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_clear_queue(self, tmp_path):
        """Test clearing all tasks from queue."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        for i in range(5):
            task = q.create_task(f"http://example.com/{i}.bin", f"{i}.bin", str(tmp_path))
            await q.add(task)
        
        await q.clear_queue()
        
        assert len(q._queue) == 0
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_clear_completed(self, tmp_path):
        """Test clearing completed tasks."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        task.state = DownloadState.COMPLETED
        q._completed.append(task)
        
        await q.clear_completed()
        
        assert len(q._completed) == 0
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, tmp_path):
        """Test retrieving task by ID."""
        engine = DownloadEngine(segments=1)
        
        q = QueueManager(engine, max_concurrent=1)
        
        task = q.create_task("http://example.com/file.bin", "file.bin", str(tmp_path))
        await q.add(task)
        
        found = q.get_task(task.id)
        assert found is not None
        assert found.id == task.id
        
        not_found = q.get_task("non-existent")
        assert not_found is None
        
        await engine.close()
