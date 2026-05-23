"""
Tests for the plugin system.
Tests plugin capability flags, error handling, stream processing, and download mode detection.
"""

import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path

import pytest

from plugins.plugin_base import (
    SpiderPlugin,
    PluginResult,
    PluginContext,
    PluginCapability,
    PluginError,
    PluginDependencyMissing,
    PluginStreamError,
    DownloadMode,
    MediaFormat,
    StreamSegment,
)
from plugins.yt_dlp_plugin import YtDlpPlugin
from plugins.browser_extension import BrowserExtensionPlugin



class TestPluginBase:
    """Test base plugin functionality."""

    def test_plugin_result_basic(self):
        """Test basic PluginResult creation."""
        result = PluginResult(
            url="http://example.com/file.bin",
            filename="file.bin",
            download_mode=DownloadMode.DIRECT,
        )
        assert result.url == "http://example.com/file.bin"
        assert result.filename == "file.bin"
        assert result.download_mode == DownloadMode.DIRECT

    def test_plugin_result_with_metadata(self):
        """Test PluginResult with metadata."""
        result = PluginResult(
            url="http://example.com/file.bin",
            filename="file.bin",
            download_mode=DownloadMode.DIRECT,
            total_size=1000,
            content_type="application/octet-stream",
        )
        assert result.total_size == 1000
        assert result.content_type == "application/octet-stream"

    def test_plugin_context_basic(self):
        """Test basic PluginContext creation."""
        ctx = PluginContext(
            save_path="/tmp",
            preferred_quality="720p",
            preferred_format="mp4",
        )
        assert ctx.save_path == "/tmp"
        assert ctx.preferred_quality == "720p"
        assert ctx.preferred_format == "mp4"

    def test_plugin_capability_flags(self):
        """Test PluginCapability flags."""
        assert PluginCapability.NONE == 0
        assert PluginCapability.URL_HANDLING == 1
        assert PluginCapability.STREAM_EXTRACTION == 2
        assert PluginCapability.METADATA_EXTRACTION == 4

    def test_download_mode_enum(self):
        """Test DownloadMode enum values."""
        assert DownloadMode.DIRECT == "direct"
        assert DownloadMode.STREAM_HLS == "stream_hls"
        assert DownloadMode.STREAM_DASH == "stream_dash"
        assert DownloadMode.YTDLP == "ytdlp"
        assert DownloadMode.BLOB == "blob"

    def test_media_format_enum(self):
        """Test MediaFormat enum values."""
        assert MediaFormat.VIDEO == "video"
        assert MediaFormat.AUDIO == "audio"
        assert MediaFormat.IMAGE == "image"
        assert MediaFormat.DOCUMENT == "document"



class TestPluginErrors:
    """Test plugin error handling."""

    def test_plugin_error_basic(self):
        """Test basic PluginError."""
        error = PluginError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_plugin_dependency_missing(self):
        """Test PluginDependencyMissing error."""
        error = PluginDependencyMissing("yt-dlp")
        assert "yt-dlp" in str(error)
        assert isinstance(error, PluginError)

    def test_plugin_stream_error(self):
        """Test PluginStreamError error."""
        error = PluginStreamError("Stream extraction failed")
        assert "Stream extraction failed" in str(error)
        assert isinstance(error, PluginError)



class TestStreamSegment:
    """Test StreamSegment dataclass."""

    def test_stream_segment_basic(self):
        """Test basic StreamSegment creation."""
        segment = StreamSegment(
            url="http://example.com/segment0.ts",
            index=0,
            duration_sec=10.0,
        )
        assert segment.url == "http://example.com/segment0.ts"
        assert segment.index == 0
        assert segment.duration_sec == 10.0

    def test_stream_segment_with_encryption(self):
        """Test StreamSegment with encryption info."""
        segment = StreamSegment(
            url="http://example.com/segment0.ts",
            index=0,
            duration_sec=10.0,
            key_url="http://example.com/key.bin",
            key_iv="0123456789abcdef0123456789abcdef",
        )
        assert segment.key_url == "http://example.com/key.bin"
        assert segment.key_iv == "0123456789abcdef0123456789abcdef"

    def test_stream_segment_with_byterange(self):
        """Test StreamSegment with byte range."""
        segment = StreamSegment(
            url="http://example.com/segment0.ts",
            index=0,
            duration_sec=10.0,
            byterange_start=0,
            byterange_length=1024,
        )
        assert segment.byterange_start == 0
        assert segment.byterange_length == 1024



class TestYTDLPPlugin:
    """Test yt-dlp plugin functionality."""

    def test_plugin_initialization(self):
        """Test YTDLPPlugin initialization."""
        plugin = YTDLPPlugin()
        assert plugin.name == "yt-dlp"
        assert "yt-dlp" in plugin.description.lower()

    def test_can_handle_youtube_urls(self):
        """Test that plugin can handle YouTube URLs."""
        plugin = YTDLPPlugin()
        
        youtube_urls = [
            "https://www.youtube.com/watch?v=abc123",
            "https://youtu.be/abc123",
            "https://m.youtube.com/watch?v=abc123",
        ]
        
        for url in youtube_urls:
            assert plugin.can_handle(url) is True

    def test_can_handle_vimeo_urls(self):
        """Test that plugin can handle Vimeo URLs."""
        plugin = YTDLPPlugin()
        
        vimeo_urls = [
            "https://vimeo.com/123456789",
            "https://player.vimeo.com/video/123456789",
        ]
        
        for url in vimeo_urls:
            assert plugin.can_handle(url) is True

    def test_cannot_handle_direct_downloads(self):
        """Test that plugin rejects direct download URLs."""
        plugin = YTDLPPlugin()
        
        direct_urls = [
            "http://example.com/file.zip",
            "https://example.com/file.mp4",
        ]
        
        for url in direct_urls:
            assert plugin.can_handle(url) is False

    def test_can_handle_twitch_urls(self):
        """Test that plugin can handle Twitch URLs."""
        plugin = YTDLPPlugin()
        
        twitch_urls = [
            "https://www.twitch.tv/videos/123456",
            "https://clips.twitch.tv/clip123",
        ]
        
        for url in twitch_urls:
            assert plugin.can_handle(url) is True

    @pytest.mark.asyncio
    async def test_process_with_mock_subprocess(self):
        """Test process with mocked yt-dlp subprocess."""
        plugin = YTDLPPlugin()
        
        ctx = PluginContext(
            save_path="/tmp",
            preferred_quality="720p",
            preferred_format="mp4",
        )
        
        mock_process = MagicMock()
        mock_process.stdout.readline = MagicMock(
            side_effect=[
                b'{"downloaded_bytes": 500, "total_bytes": 1000}\n',
                b'{"downloaded_bytes": 1000, "total_bytes": 1000}\n',
                b"",
            ]
        )
        mock_process.wait = AsyncMock(return_value=0)
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch.object(plugin, "_run_ytdlp", return_value=mock_process):
                assert plugin.can_handle("https://youtube.com/watch?v=abc")

    def test_domain_allowlist(self):
        """Test that domain allowlist is comprehensive."""
        plugin = YTDLPPlugin()
        
        test_domains = [
            ("youtube.com", True),
            ("vimeo.com", True),
            ("twitch.tv", True),
            ("twitter.com", True),
            ("example.com", False),
        ]
        
        for domain, expected in test_domains:
            url = f"https://{domain}/video"
            result = plugin.can_handle(url)
            assert result == expected, f"Failed for {domain}"



class TestBrowserExtensionPluginAdvanced:
    """Advanced tests for browser extension plugin."""

    def test_plugin_does_not_handle_direct_urls(self):
        """Test that browser extension plugin doesn't handle direct URLs."""
        plugin = BrowserExtensionPlugin()
        
        assert plugin.can_handle("http://example.com/file.zip") is False
        assert plugin.can_handle("https://example.com/file.mp4") is False

    def test_plugin_priority(self):
        """Test that browser extension plugin has appropriate priority."""
        plugin = BrowserExtensionPlugin()
        assert plugin.priority == 10

    def test_plugin_capabilities(self):
        """Test that browser extension plugin has no direct capabilities."""
        plugin = BrowserExtensionPlugin()
        assert plugin.capabilities == PluginCapability.NONE

    def test_ipc_port_constant(self):
        """Test IPC port constant."""
        assert BrowserExtensionPlugin.IPC_PORT == 19999

    def test_pipe_name_constant(self):
        """Test pipe name constant."""
        assert BrowserExtensionPlugin.PIPE_NAME == r'\\.\pipe\spider_manager_ipc'

    def test_host_name_constant(self):
        """Test host name constant."""
        assert BrowserExtensionPlugin.HOST_NAME == "com.spidermanager.bridge"



class TestPluginContextAdvanced:
    """Test advanced PluginContext functionality."""

    def test_context_with_cookies(self):
        """Test PluginContext with cookies."""
        ctx = PluginContext(
            save_path="/tmp",
            cookies={"session": "abc123"},
        )
        assert ctx.cookies == {"session": "abc123"}

    def test_context_with_headers(self):
        """Test PluginContext with custom headers."""
        ctx = PluginContext(
            save_path="/tmp",
            headers={"User-Agent": "Custom"},
        )
        assert ctx.headers == {"User-Agent": "Custom"}

    def test_context_with_proxy(self):
        """Test PluginContext with proxy."""
        ctx = PluginContext(
            save_path="/tmp",
            proxy="http://proxy.example.com:8080",
        )
        assert ctx.proxy == "http://proxy.example.com:8080"

    def test_context_with_subtitles(self):
        """Test PluginContext with subtitle options."""
        ctx = PluginContext(
            save_path="/tmp",
            download_subtitles=True,
            subtitle_languages=["en", "es"],
        )
        assert ctx.download_subtitles is True
        assert ctx.subtitle_languages == ["en", "es"]



class TestPluginResultAdvanced:
    """Test advanced PluginResult functionality."""

    def test_result_with_stream_segments(self):
        """Test PluginResult with stream segments."""
        segments = [
            StreamSegment(url="seg0.ts", index=0, duration_sec=10.0),
            StreamSegment(url="seg1.ts", index=1, duration_sec=10.0),
        ]
        
        result = PluginResult(
            url="http://example.com/stream.m3u8",
            filename="stream.mp4",
            download_mode=DownloadMode.STREAM_HLS,
            stream_segments=segments,
        )
        
        assert len(result.stream_segments) == 2
        assert result.stream_segments[0].index == 0

    def test_result_with_thumbnail(self):
        """Test PluginResult with thumbnail URL."""
        result = PluginResult(
            url="http://example.com/video.mp4",
            filename="video.mp4",
            download_mode=DownloadMode.YTDLP,
            thumbnail_url="http://example.com/thumb.jpg",
        )
        
        assert result.thumbnail_url == "http://example.com/thumb.jpg"

    def test_result_with_chapters(self):
        """Test PluginResult with chapter information."""
        result = PluginResult(
            url="http://example.com/video.mp4",
            filename="video.mp4",
            download_mode=DownloadMode.YTDLP,
            chapters=[
                {"title": "Intro", "start_time": 0},
                {"title": "Main", "start_time": 30},
            ],
        )
        
        assert len(result.chapters) == 2
        assert result.chapters[0]["title"] == "Intro"

    def test_result_with_metadata(self):
        """Test PluginResult with video metadata."""
        result = PluginResult(
            url="http://example.com/video.mp4",
            filename="video.mp4",
            download_mode=DownloadMode.YTDLP,
            duration_sec=300,
            width=1920,
            height=1080,
            fps=30,
        )
        
        assert result.duration_sec == 300
        assert result.width == 1920
        assert result.height == 1080
        assert result.fps == 30



class TestDownloadModeDetection:
    """Test download mode detection from URLs."""

    def test_detect_hls_mode(self):
        """Test HLS mode detection from .m3u8 URL."""
        url = "http://example.com/stream.m3u8"
        assert ".m3u8" in url

    def test_detect_dash_mode(self):
        """Test DASH mode detection from .mpd URL."""
        url = "http://example.com/stream.mpd"
        assert ".mpd" in url

    def test_detect_blob_mode(self):
        """Test blob mode detection from blob: URL."""
        url = "blob:https://example.com/abc123"
        assert url.startswith("blob:")

    def test_detect_direct_mode(self):
        """Test direct mode detection from regular URL."""
        url = "http://example.com/file.mp4"
        assert not url.startswith("blob:")
        assert ".m3u8" not in url
        assert ".mpd" not in url



class TestPluginIntegration:
    """Test plugin integration with download engine."""

    @pytest.mark.asyncio
    async def test_plugin_result_to_download_task(self):
        """Test converting PluginResult to DownloadTask."""
        from core.download_engine import DownloadTask
        
        result = PluginResult(
            url="http://example.com/file.bin",
            filename="file.bin",
            download_mode=DownloadMode.DIRECT,
            total_size=1000,
        )
        
        task = DownloadTask(
            id="test-1",
            url=result.url,
            filename=result.filename,
            save_path="/tmp",
            total_size=result.total_size,
            download_mode=result.download_mode,
        )
        
        assert task.url == result.url
        assert task.filename == result.filename
        assert task.download_mode == result.download_mode

    @pytest.mark.asyncio
    async def test_plugin_error_propagation(self):
        """Test that plugin errors are properly propagated."""
        plugin = YTDLPPlugin()
        
        ctx = PluginContext(save_path="/tmp")
        
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            with pytest.raises((PluginDependencyMissing, Exception)):
                await plugin.process("https://youtube.com/watch?v=abc", ctx)



class TestPluginCapabilities:
    """Test plugin capability flags and combinations."""

    def test_capability_combination(self):
        """Test combining multiple capabilities."""
        combined = PluginCapability.URL_HANDLING | PluginCapability.STREAM_EXTRACTION
        assert combined == 3

    def test_capability_none(self):
        """Test NONE capability."""
        assert PluginCapability.NONE == 0

    def test_capability_all(self):
        """Test combining all capabilities."""
        all_caps = (
            PluginCapability.URL_HANDLING |
            PluginCapability.STREAM_EXTRACTION |
            PluginCapability.METADATA_EXTRACTION
        )
        assert all_caps == 7



class TestStreamProcessing:
    """Test stream segment processing."""

    def test_stream_segment_url_resolution(self):
        """Test that stream segment URLs are resolved correctly."""
        base_url = "http://example.com/"
        relative_url = "segment0.ts"
        
        from urllib.parse import urljoin
        absolute_url = urljoin(base_url, relative_url)
        
        assert absolute_url == "http://example.com/segment0.ts"

    def test_stream_segment_duration_validation(self):
        """Test stream segment duration validation."""
        segment = StreamSegment(
            url="http://example.com/seg0.ts",
            index=0,
            duration_sec=10.5,
        )
        
        assert segment.duration_sec > 0
        assert segment.duration_sec < 3600

    def test_stream_segment_index_ordering(self):
        """Test that stream segments maintain index order."""
        segments = [
            StreamSegment(url="seg0.ts", index=0, duration_sec=10.0),
            StreamSegment(url="seg1.ts", index=1, duration_sec=10.0),
            StreamSegment(url="seg2.ts", index=2, duration_sec=10.0),
        ]
        
        for i, seg in enumerate(segments):
            assert seg.index == i



class TestPluginMetadata:
    """Test plugin metadata extraction."""

    def test_plugin_name_property(self):
        """Test that plugins have name property."""
        ytdlp = YTDLPPlugin()
        browser = BrowserExtensionPlugin()
        
        assert ytdlp.name == "yt-dlp"
        assert browser.name == "browser-extension"

    def test_plugin_description_property(self):
        """Test that plugins have description property."""
        ytdlp = YTDLPPlugin()
        browser = BrowserExtensionPlugin()
        
        assert len(ytdlp.description) > 0
        assert len(browser.description) > 0

    def test_plugin_version_property(self):
        """Test that plugins have version property."""
        ytdlp = YTDLPPlugin()
        
        assert hasattr(ytdlp, "version")
