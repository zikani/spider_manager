import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

from core.download_engine import DownloadEngine, DownloadTask
from core.resume_handler import hydrate_partial_segments


def test_probe_parses_headers():
    """Test _parse_probe_response static method directly."""
    class MockResponse:
        headers = {
            "Content-Length": "1024",
            "Content-Disposition": 'attachment; filename="test.bin"',
            "Accept-Ranges": "bytes",
            "Content-Type": "application/octet-stream",
        }
        url = "https://x/test.bin"
        status = 200
        ok = True
        
        async def raise_for_status(self):
            pass
    
    mock_resp = MockResponse()
    info = DownloadEngine._parse_probe_response(mock_resp, str(mock_resp.url))
    
    assert info["size"] == 1024
    assert info["filename"] == "test.bin"
    assert info["resumable"] is True


def test_plan_segments():
    engine = DownloadEngine(segments=4)
    task = DownloadTask(
        id="1",
        url="u",
        filename="f.bin",
        save_path="/tmp",
        total_size=100,
    )
    segs = engine._plan_segments(task)
    assert len(segs) >= 1
    assert segs[0].start == 0
    assert segs[-1].end == task.total_size - 1


def test_merge_creates_final_file(tmp_path):
    async def _run():
        engine = DownloadEngine(segments=1)
        base = tmp_path / "out.bin"
        task = DownloadTask(
            id="1",
            url="u",
            filename="out.bin",
            save_path=str(tmp_path),
            total_size=8,
        )
        task.segments = engine._plan_segments(task)
        p0 = task.segments[0].temp_path
        with open(p0, "wb") as f:
            f.write(b"12345678")
        task.segments[0].complete = True
        await engine._merge_and_verify(task)
        assert base.is_file()
        assert base.read_bytes() == b"12345678"
        assert not os.path.exists(p0)
        await engine.close()

    asyncio.run(_run())


def test_hydrate_partial_segments(tmp_path):
    task = DownloadTask(
        id="1",
        url="u",
        filename="f.bin",
        save_path=str(tmp_path),
        total_size=10,
    )
    engine = DownloadEngine(segments=2)
    task.segments = engine._plan_segments(task)
    p0 = task.segments[0].temp_path
    with open(p0, "wb") as f:
        f.write(b"12345")
    hydrate_partial_segments(task)
    assert task.segments[0].downloaded == 5
    assert task.downloaded == 5
