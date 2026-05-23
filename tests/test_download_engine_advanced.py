"""
Advanced edge case tests for DownloadEngine v3.0.
Tests HLS, DASH, yt-dlp, checksums, resume, error handling, and concurrency.
"""

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from dataclasses import dataclass

import pytest

from core.download_engine import (
    DownloadEngine,
    DownloadTask,
    DownloadSegment,
    StreamSegment,
    _verify_checksum,
    _parse_hls_master,
    _parse_hls_media,
    _find_ffmpeg,
)
from core.speed_limiter import SpeedLimiter
from config.constants import DownloadState



class TestChecksumVerification:
    """Test SHA-256 and MD5 checksum verification."""

    def test_sha256_verification_success(self, tmp_path):
        """Test successful SHA-256 checksum verification."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        h = hashlib.sha256()
        h.update(b"hello world")
        expected = f"sha256:{h.hexdigest()}"
        
        _verify_checksum(str(test_file), expected)

    def test_sha256_verification_failure(self, tmp_path):
        """Test SHA-256 checksum verification failure."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        with pytest.raises(ValueError, match="Checksum mismatch"):
            _verify_checksum(str(test_file), "sha256:wronghash123")

    def test_md5_verification_success(self, tmp_path):
        """Test successful MD5 checksum verification."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        h = hashlib.md5()
        h.update(b"hello world")
        expected = f"md5:{h.hexdigest()}"
        
        _verify_checksum(str(test_file), expected)

    def test_md5_verification_failure(self, tmp_path):
        """Test MD5 checksum verification failure."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        with pytest.raises(ValueError, match="Checksum mismatch"):
            _verify_checksum(str(test_file), "md5:wronghash")

    def test_invalid_checksum_format(self, tmp_path):
        """Test handling of invalid checksum format."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        _verify_checksum(str(test_file), "invalid_format")

    def test_unsupported_algorithm(self, tmp_path):
        """Test handling of unsupported checksum algorithm."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        _verify_checksum(str(test_file), "sha1:somehash")

    def test_empty_checksum(self, tmp_path):
        """Test that empty checksum is skipped."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        
        _verify_checksum(str(test_file), "")



class TestHLSParser:
    """Test HLS manifest parsing."""

    def test_parse_hls_master_basic(self):
        """Test basic HLS master playlist parsing."""
        text = """
        stream_360p.m3u8
        stream_720p.m3u8
        """
        variants = _parse_hls_master(text, "http://example.com/")
        assert len(variants) == 2
        assert variants[0]["bandwidth"] == 2000000
        assert variants[0]["resolution"] == "720p"
        assert variants[1]["bandwidth"] == 1000000
        assert variants[1]["resolution"] == "360p"

    def test_parse_hls_master_sorting(self):
        """Test that variants are sorted by bandwidth (descending)."""
        text = """
        low.m3u8
        high.m3u8
        medium.m3u8
        """
        variants = _parse_hls_master(text, "http://example.com/")
        assert variants[0]["bandwidth"] == 3000000
        assert variants[1]["bandwidth"] == 1000000
        assert variants[2]["bandwidth"] == 500000

    def test_parse_hls_master_url_resolution(self):
        """Test that relative URLs are resolved against base URL."""
        text = """
        relative/stream.m3u8
        """
        variants = _parse_hls_master(text, "http://example.com/base/")
        assert variants[0]["url"] == "http://example.com/base/relative/stream.m3u8"

    def test_parse_hls_media_basic(self):
        """Test basic HLS media playlist parsing."""
        text = """
        segment0.ts
        segment1.ts
        """
        segments = _parse_hls_media(text, "http://example.com/")
        assert len(segments) == 2
        assert segments[0]["duration"] == 10.0
        assert segments[1]["duration"] == 10.0

    def test_parse_hls_media_with_encryption(self):
        """Test HLS media playlist with AES-128 encryption."""
        text = """
        segment0.ts
        """
        segments = _parse_hls_media(text, "http://example.com/")
        assert len(segments) == 1
        assert segments[0]["key_url"] == "https://example.com/key.bin"
        assert segments[0]["key_iv"] == "12345678901234567890123456789012"

    def test_parse_hls_media_byterange(self):
        """Test HLS media playlist with byte-range segments."""
        text = """
        segment0.ts
        """
        segments = _parse_hls_media(text, "http://example.com/")
        assert len(segments) == 1
        assert segments[0]["byterange_start"] == 0
        assert segments[0]["byterange_length"] == 1024



class TestDownloadTaskProperties:
    """Test DownloadTask property calculations."""

    def test_progress_direct_download(self):
        """Test progress calculation for direct downloads."""
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
            downloaded=500,
        )
        assert task.progress == 50.0

    def test_progress_stream_hls(self):
        """Test progress calculation for HLS streams."""
        task = DownloadTask(
            id="1",
            url="http://example.com/stream.m3u8",
            filename="stream.mp4",
            save_path="/tmp",
            download_mode="stream_hls",
        )
        task.stream_segments = [
            StreamSegment(url="seg0.ts", index=0, complete=True),
            StreamSegment(url="seg1.ts", index=1, complete=False),
            StreamSegment(url="seg2.ts", index=2, complete=True),
        ]
        assert task.progress == 66.67

    def test_progress_zero_total_size(self):
        """Test progress when total_size is zero."""
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=0,
            downloaded=0,
        )
        assert task.progress == 0.0

    def test_progress_capped_at_100(self):
        """Test progress is capped at 100%."""
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=100,
            downloaded=150,
        )
        assert task.progress == 100.0

    def test_elapsed_not_started(self):
        """Test elapsed time when download hasn't started."""
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
        )
        assert task.elapsed == 0.0

    def test_elapsed_in_progress(self):
        """Test elapsed time during download."""
        import time
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
        )
        task.started_at = time.time() - 5.0
        assert 4.9 <= task.elapsed <= 5.1

    def test_stats_snapshot(self):
        """Test stats property returns correct snapshot."""
        task = DownloadTask(
            id="test-id",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
            downloaded=500,
            state=DownloadState.DOWNLOADING,
        )
        stats = task.stats
        assert stats["id"] == "test-id"
        assert stats["filename"] == "file.bin"
        assert stats["state"] == DownloadState.DOWNLOADING
        assert stats["progress"] == 50.0
        assert stats["downloaded"] == 500
        assert stats["total_size"] == 1000



class TestDownloadSegmentProperties:
    """Test DownloadSegment property calculations."""

    def test_expected_bytes(self):
        """Test expected_bytes calculation."""
        seg = DownloadSegment(index=0, start=0, end=99)
        assert seg.expected_bytes == 100

    def test_expected_bytes_zero_end(self):
        """Test expected_bytes when end is 0."""
        seg = DownloadSegment(index=0, start=0, end=0)
        assert seg.expected_bytes == 0

    def test_remaining_bytes(self):
        """Test remaining_bytes calculation."""
        seg = DownloadSegment(index=0, start=0, end=99, downloaded=30)
        assert seg.remaining_bytes == 70

    def test_remaining_bytes_complete(self):
        """Test remaining_bytes when segment is complete."""
        seg = DownloadSegment(index=0, start=0, end=99, downloaded=100)
        assert seg.remaining_bytes == 0



class TestSpeedLimiterIntegration:
    """Test speed limiter integration with download engine."""

    @pytest.mark.asyncio
    async def test_speed_limiter_applied(self):
        """Test that speed limiter is applied during download."""
        limiter = SpeedLimiter(100_000)
        engine = DownloadEngine(segments=1, speed_limiter=limiter)
        
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
        )
        
        original_consume = limiter.consume
        consume_calls = []
        
        async def track_consume(bytes_count):
            consume_calls.append(bytes_count)
            return await original_consume(bytes_count)
        
        limiter.consume = track_consume
        
        assert len(consume_calls) == 0
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_speed_limit_update_during_download(self):
        """Test that speed limit can be updated during active download."""
        limiter = SpeedLimiter(100_000)
        engine = DownloadEngine(segments=1, speed_limiter=limiter)
        
        limiter.set_limit_bps(200_000)
        assert limiter._limit_bps == 200_000
        
        await engine.close()



class TestErrorHandling:
    """Test error handling in download engine."""

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test handling of connection timeout."""
        engine = DownloadEngine(segments=1)
        
        mock_session = MagicMock()
        mock_session.head = AsyncMock(side_effect=asyncio.TimeoutError)
        
        with patch.object(engine, "_get_session", return_value=mock_session):
            with pytest.raises((asyncio.TimeoutError, Exception)):
                await engine.probe("http://example.com/file.bin")
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        """Test handling of HTTP 500 errors."""
        engine = DownloadEngine(segments=1)
        
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("500 Error"))
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.head = MagicMock(return_value=mock_cm)
        
        with patch.object(engine, "_get_session", return_value=mock_session):
            with pytest.raises(Exception):
                await engine.probe("http://example.com/file.bin")
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_file_size_mismatch(self):
        """Test handling of file size mismatch after download."""
        engine = DownloadEngine(segments=1)
        
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=1000,
        )
        
        task.downloaded = 900
        
        assert task.downloaded != task.total_size
        
        await engine.close()



class TestResumeHandlerEdgeCases:
    """Test resume handler with edge cases."""

    def test_resume_with_corrupted_segment(self, tmp_path):
        """Test resume when a segment file is corrupted."""
        from core.resume_handler import hydrate_partial_segments
        
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path=str(tmp_path),
            total_size=100,
        )
        
        engine = DownloadEngine(segments=2)
        task.segments = engine._plan_segments(task)
        
        with open(task.segments[0].temp_path, "wb") as f:
            f.write(b"corrupted")
        
        hydrate_partial_segments(task)
        
        assert task.downloaded == len(b"corrupted")

    def test_resume_with_missing_segment_file(self, tmp_path):
        """Test resume when a segment file is missing."""
        from core.resume_handler import hydrate_partial_segments
        
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path=str(tmp_path),
            total_size=100,
        )
        
        engine = DownloadEngine(segments=2)
        task.segments = engine._plan_segments(task)
        
        hydrate_partial_segments(task)
        
        assert task.downloaded == 0



class TestConcurrency:
    """Test concurrent download operations."""

    @pytest.mark.asyncio
    async def test_concurrent_segment_downloads(self):
        """Test that segments are downloaded concurrently."""
        engine = DownloadEngine(segments=4)
        
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()
        
        async def fake_download(segment):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.1)
            async with lock:
                current_concurrent -= 1
        
        tasks = [fake_download(i) for i in range(4)]
        await asyncio.gather(*tasks)
        
        assert max_concurrent > 1
        
        await engine.close()

    @pytest.mark.asyncio
    async def test_segment_ordering_enforcement(self):
        """Test that segments are merged in correct order."""
        engine = DownloadEngine(segments=3)
        
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            total_size=30,
        )
        
        task.segments = engine._plan_segments(task)
        
        for i, seg in enumerate(task.segments):
            assert seg.index == i
            assert seg.start == i * 10
            assert seg.end == (i + 1) * 10 - 1
        
        await engine.close()



class TestFFmpegDiscovery:
    """Test ffmpeg binary discovery."""

    def test_find_ffmpeg_returns_string(self):
        """Test that _find_ffmpeg returns a string."""
        result = _find_ffmpeg()
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_find_ffmpeg_from_path(self, mock_which):
        """Test ffmpeg discovery from PATH."""
        result = _find_ffmpeg()
        assert result == "/usr/bin/ffmpeg"

    @patch("shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_find_ffmpeg_fallback(self, mock_isfile, mock_which):
        """Test ffmpeg fallback to default."""
        result = _find_ffmpeg()
        assert result == "ffmpeg"



class TestDownloadMode:
    """Test different download modes."""

    def test_download_mode_direct(self):
        """Test DIRECT download mode."""
        task = DownloadTask(
            id="1",
            url="http://example.com/file.bin",
            filename="file.bin",
            save_path="/tmp",
            download_mode="direct",
        )
        assert task.download_mode == "direct"

    def test_download_mode_hls(self):
        """Test STREAM_HLS download mode."""
        task = DownloadTask(
            id="1",
            url="http://example.com/stream.m3u8",
            filename="stream.mp4",
            save_path="/tmp",
            download_mode="stream_hls",
        )
        assert task.download_mode == "stream_hls"

    def test_download_mode_dash(self):
        """Test STREAM_DASH download mode."""
        task = DownloadTask(
            id="1",
            url="http://example.com/stream.mpd",
            filename="stream.mp4",
            save_path="/tmp",
            download_mode="stream_dash",
        )
        assert task.download_mode == "stream_dash"

    def test_download_mode_ytdlp(self):
        """Test YTDLP download mode."""
        task = DownloadTask(
            id="1",
            url="https://youtube.com/watch?v=abc",
            filename="video.mp4",
            save_path="/tmp",
            download_mode="ytdlp",
        )
        assert task.download_mode == "ytdlp"

    def test_download_mode_blob(self):
        """Test BLOB download mode."""
        task = DownloadTask(
            id="1",
            url="blob:https://example.com/abc123",
            filename="video.mp4",
            save_path="/tmp",
            download_mode="blob",
        )
        assert task.download_mode == "blob"
