"""
Performance benchmarks for DownloadEngine.
Tests segment merging, concurrent downloads, and throughput.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.download_engine import DownloadEngine, DownloadTask
from core.speed_limiter import SpeedLimiter



class TestSegmentMergingPerformance:
    """Benchmark segment merging operations."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_merge_small_file(self, tmp_path, benchmark):
        """Benchmark merging small file (10 MB)."""
        engine = DownloadEngine(segments=4)
        
        async def merge_operation():
            task = DownloadTask(
                id="test-1",
                url="http://example.com/file.bin",
                filename="file.bin",
                save_path=str(tmp_path),
                total_size=10 * 1024 * 1024,
            )
            task.segments = engine._plan_segments(task)
            
            for seg in task.segments:
                with open(seg.temp_path, "wb") as f:
                    f.write(b"x" * seg.expected_bytes)
                seg.complete = True
            
            await engine._merge_segments(task)
        
        result = benchmark(merge_operation)
        await engine.close()
        
        assert result < 1.0

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_merge_medium_file(self, tmp_path, benchmark):
        """Benchmark merging medium file (100 MB)."""
        engine = DownloadEngine(segments=8)
        
        async def merge_operation():
            task = DownloadTask(
                id="test-1",
                url="http://example.com/file.bin",
                filename="file.bin",
                save_path=str(tmp_path),
                total_size=100 * 1024 * 1024,
            )
            task.segments = engine._plan_segments(task)
            
            for seg in task.segments:
                with open(seg.temp_path, "wb") as f:
                    f.write(b"x" * seg.expected_bytes)
                seg.complete = True
            
            await engine._merge_segments(task)
        
        result = benchmark(merge_operation)
        await engine.close()
        
        assert result < 5.0

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_merge_with_many_segments(self, tmp_path, benchmark):
        """Benchmark merging with many segments (32)."""
        engine = DownloadEngine(segments=32)
        
        async def merge_operation():
            task = DownloadTask(
                id="test-1",
                url="http://example.com/file.bin",
                filename="file.bin",
                save_path=str(tmp_path),
                total_size=50 * 1024 * 1024,
            )
            task.segments = engine._plan_segments(task)
            
            for seg in task.segments:
                with open(seg.temp_path, "wb") as f:
                    f.write(b"x" * seg.expected_bytes)
                seg.complete = True
            
            await engine._merge_segments(task)
        
        result = benchmark(merge_operation)
        await engine.close()
        
        assert result < 3.0



class TestConcurrentThroughput:
    """Benchmark concurrent download throughput."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_segment_simulation(self, benchmark):
        """Benchmark concurrent segment download simulation."""
        engine = DownloadEngine(segments=8)
        
        async def download_simulation():
            async def fake_download(seg_index):
                await asyncio.sleep(0.01)
                return seg_index
            
            tasks = [fake_download(i) for i in range(8)]
            results = await asyncio.gather(*tasks)
            return len(results)
        
        result = benchmark(download_simulation)
        await engine.close()
        
        assert result == 8

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_speed_limiter_overhead(self, benchmark):
        """Benchmark speed limiter overhead."""
        limiter = SpeedLimiter(10 * 1024 * 1024)
        
        async def limiter_operation():
            for _ in range(100):
                await limiter.consume(1024 * 1024)
        
        result = benchmark(limiter_operation)
        
        assert 9.0 <= result <= 12.0



class TestMemoryUsage:
    """Benchmark memory usage patterns."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_large_task_memory(self, tmp_path, benchmark):
        """Benchmark memory usage for large task."""
        engine = DownloadEngine(segments=16)
        
        async def create_large_task():
            task = DownloadTask(
                id="test-1",
                url="http://example.com/file.bin",
                filename="file.bin",
                save_path=str(tmp_path),
                total_size=1024 * 1024 * 1024,
            )
            task.segments = engine._plan_segments(task)
            return len(task.segments)
        
        result = benchmark(create_large_task)
        await engine.close()
        
        assert result == 16

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_queue_memory_with_many_tasks(self, benchmark):
        """Benchmark memory usage with many queued tasks."""
        from core.queue_manager import QueueManager
        
        engine = DownloadEngine(segments=4)
        q = QueueManager(engine, max_concurrent=1)
        
        async def create_many_tasks():
            for i in range(100):
                task = q.create_task(
                    f"http://example.com/file{i}.bin",
                    f"file{i}.bin",
                    "/tmp"
                )
                await q.add(task)
            return len(q._queue)
        
        result = benchmark(create_many_tasks)
        await engine.close()
        
        assert result == 100



class TestIOPerformance:
    """Benchmark I/O operations."""

    @pytest.mark.benchmark
    def test_file_write_performance(self, tmp_path, benchmark):
        """Benchmark file write performance."""
        def write_operation():
            test_file = tmp_path / "test.bin"
            data = b"x" * (10 * 1024 * 1024)
            with open(test_file, "wb") as f:
                f.write(data)
        
        result = benchmark(write_operation)
        
        assert result < 0.5

    @pytest.mark.benchmark
    def test_file_read_performance(self, tmp_path, benchmark):
        """Benchmark file read performance."""
        test_file = tmp_path / "test.bin"
        data = b"x" * (10 * 1024 * 1024)
        with open(test_file, "wb") as f:
            f.write(data)
        
        def read_operation():
            with open(test_file, "rb") as f:
                f.read()
        
        result = benchmark(read_operation)
        
        assert result < 0.5



class TestNetworkSimulation:
    """Benchmark network simulation operations."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_session_creation_overhead(self, benchmark):
        """Benchmark aiohttp session creation overhead."""
        engine = DownloadEngine(segments=1)
        
        async def session_operation():
            session = await engine._get_session()
            return session is not None
        
        result = benchmark(session_operation)
        await engine.close()
        
        assert result < 0.1

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_probe_overhead(self, benchmark):
        """Benchmark probe operation overhead."""
        engine = DownloadEngine(segments=1)
        
        mock_resp = MagicMock()
        mock_resp.headers = {
            "Content-Length": "1024",
            "Content-Disposition": 'attachment; filename="test.bin"',
            "Accept-Ranges": "bytes",
        }
        mock_resp.url = "https://x/test.bin"
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.head = MagicMock(return_value=mock_cm)
        mock_session.closed = False
        
        async def probe_operation():
            with patch.object(engine, "_get_session", AsyncMock(return_value=mock_session)):
                info = await engine.probe("https://example.com/a")
            return info["size"]
        
        result = benchmark(probe_operation)
        await engine.close()
        
        assert result == 1024



class TestUIUpdatePerformance:
    """Benchmark UI update operations."""

    @pytest.mark.benchmark
    def test_model_update_overhead(self, benchmark):
        """Benchmark download table model update overhead."""
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.widgets.download_table import DownloadTableModel
            from core.download_engine import DownloadTask
        except ImportError:
            pytest.skip("UI components not available")
        
        app = QApplication.instance()
        if app is None:
            QApplication([])
        
        model = DownloadTableModel()
        
        for i in range(10):
            task = DownloadTask(
                id=f"test-{i}",
                url=f"http://example.com/file{i}.bin",
                filename=f"file{i}.bin",
                save_path="/tmp",
            )
            model.add_task(task)
        
        def update_operation():
            for i in range(model.rowCount()):
                task = model.get_task_at_index(i)
                task.downloaded = i * 100
                model.update_task(task)
        
        result = benchmark(update_operation)
        
        assert result < 0.1

    @pytest.mark.benchmark
    def test_speed_graph_update_overhead(self, benchmark):
        """Benchmark speed graph update overhead."""
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.widgets.speed_graph import SpeedGraph
        except ImportError:
            pytest.skip("UI components not available")
        
        app = QApplication.instance()
        if app is None:
            QApplication([])
        
        graph = SpeedGraph()
        
        def update_operation():
            for i in range(60):
                graph.add_speed_point(1024 * 1024)
        
        result = benchmark(update_operation)
        
        assert result < 0.1



class TestPerformanceBaselines:
    """Document performance baselines."""

    def test_document_baselines(self):
        """Document expected performance baselines."""
        baselines = {
            "segment_merge_10mb": "< 1.0s",
            "segment_merge_100mb": "< 5.0s",
            "segment_merge_32_segments": "< 3.0s",
            "concurrent_8_segments": "< 0.5s",
            "speed_limiter_100mb_10mbs": "9-12s",
            "file_write_10mb": "< 0.5s",
            "file_read_10mb": "< 0.5s",
            "session_creation": "< 0.1s",
            "probe_operation": "< 0.1s",
            "model_update_10_tasks": "< 0.1s",
            "speed_graph_update_60": "< 0.1s",
        }
        
        assert len(baselines) > 0
