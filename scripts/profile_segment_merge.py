"""
Profiling script for segment merging operations.
Run with: python scripts/profile_segment_merge.py
"""

import cProfile
import pstats
import io
import tempfile
import asyncio
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.download_engine import DownloadEngine, DownloadTask


async def profile_segment_merge():
    """Profile segment merging with different file sizes."""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = DownloadEngine(segments=8)
        
        print("Profiling segment merge for 100 MB file...")
        task = DownloadTask(
            id="test-1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path=tmp_dir,
            total_size=100 * 1024 * 1024,
        )
        task.segments = engine._plan_segments(task)
        
        for seg in task.segments:
            with open(seg.temp_path, "wb") as f:
                f.write(b"x" * seg.expected_bytes)
            seg.complete = True
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        await engine._merge_segments(task)
        
        profiler.disable()
        
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        print(s.getvalue())
        
        await engine.close()


if __name__ == "__main__":
    asyncio.run(profile_segment_merge())
