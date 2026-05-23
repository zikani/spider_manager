"""
Memory profiling script for download engine.
Run with: python scripts/profile_memory.py
"""

import memory_profiler
import tempfile
import asyncio
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.download_engine import DownloadEngine, DownloadTask
from core.queue_manager import QueueManager


@memory_profiler.profile
async def profile_large_task_memory():
    """Profile memory usage for large download task."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = DownloadEngine(segments=16)
        
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path=tmp_dir,
            total_size=1024 * 1024 * 1024,
        )
        task.segments = engine._plan_segments(task)
        
        print(f"Created task with {len(task.segments)} segments")
        print(f"Task memory usage: {memory_profiler.memory_usage()[0]} MB")
        
        await engine.close()


@memory_profiler.profile
async def profile_queue_memory():
    """Profile memory usage for queue with many tasks."""
    engine = DownloadEngine(segments=4)
    q = QueueManager(engine, max_concurrent=1)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i in range(100):
            task = q.create_task(
                f"http://example.com/file{i}.bin",
                f"file{i}.bin",
                tmp_dir
            )
            await q.add(task)
        
        print(f"Queue has {len(q._queue)} tasks")
        print(f"Queue memory usage: {memory_profiler.memory_usage()[0]} MB")
    
    await engine.close()


if __name__ == "__main__":
    print("=== Profiling Large Task Memory ===")
    asyncio.run(profile_large_task_memory())
    
    print("\n=== Profiling Queue Memory ===")
    asyncio.run(profile_queue_memory())
