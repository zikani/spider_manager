"""
Unit tests for BitTorrent Plugin
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from plugins.torrent_plugin import TorrentPlugin, TorrentOptions
from plugins.plugin_base import PluginContext, PluginError, PluginDependencyMissing


class TestTorrentPlugin:
    """Test BitTorrent plugin functionality"""
    
    @pytest.fixture
    def plugin(self):
        return TorrentPlugin()
    
    @pytest.fixture
    def context(self):
        return PluginContext()
    
    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties"""
        assert plugin.name == "torrent"
        assert "BitTorrent" in plugin.description
        assert plugin.version == "1.0.0"
        assert plugin.author == "Spider Manager Team"
        assert plugin.priority == 55
    
    def test_can_handle_torrent_url(self, plugin):
        """Test torrent URL detection"""
        assert plugin.can_handle("magnet:?xt=urn:btih:example") is True
        assert plugin.can_handle("torrent://example.com/file.torrent") is True
        assert plugin.can_handle("http://example.com/file.torrent") is True
        assert plugin.can_handle("https://example.com/file.torrent") is True
        assert plugin.can_handle("http://example.com/file.TORRENT") is True
        assert plugin.can_handle("http://example.com/file.zip") is False
        assert plugin.can_handle("http://example.com/file.txt") is False
    
    def test_can_handle_invalid_url(self, plugin):
        """Test URL detection with invalid URLs"""
        assert plugin.can_handle("not a url") is False
        assert plugin.can_handle("") is False
    
    def test_check_libtorrent_success(self, plugin):
        """Check libtorrent availability when installed"""
        with patch('builtins.__import__'):
            plugin._check_libtorrent()  # Should not raise
    
    def test_check_libtorrent_missing(self, plugin):
        """Check libtorrent availability when not installed"""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'libtorrent'")):
            with pytest.raises(PluginDependencyMissing, match="libtorrent"):
                plugin._check_libtorrent()
    
    @pytest.mark.asyncio
    async def test_process_magnet_link(self, plugin, context):
        """Test processing magnet link"""
        url = "magnet:?xt=urn:btih:example&dn=test"
        
        with patch.object(plugin, '_check_libtorrent'):
            with patch.object(plugin, '_process_magnet', new_callable=AsyncMock) as mock_process:
                mock_result = Mock()
                mock_result.url = url
                mock_result.filename = "test"
                mock_process.return_value = mock_result
                
                result = await plugin.process(url, context)
                
                mock_process.assert_called_once_with(url, context)
                assert result.url == url
    
    @pytest.mark.asyncio
    async def test_process_torrent_file(self, plugin, context):
        """Test processing torrent file URL"""
        url = "http://example.com/file.torrent"
        
        with patch.object(plugin, '_check_libtorrent'):
            with patch.object(plugin, '_process_torrent_file', new_callable=AsyncMock) as mock_process:
                mock_result = Mock()
                mock_result.url = url
                mock_result.filename = "file.torrent"
                mock_process.return_value = mock_result
                
                result = await plugin.process(url, context)
                
                mock_process.assert_called_once_with(url, context)
                assert result.url == url
    
    def test_parse_magnet_link(self, plugin):
        """Test magnet link parsing"""
        url = "magnet:?xt=urn:btih:example&dn=TestFile&tr=tracker1&tr=tracker2"
        
        info = plugin._parse_magnet_link(url)
        
        assert info['xt'] == 'urn:btih:example'
        assert info['dn'] == 'TestFile'
        assert len(info['tr']) == 2
        assert 'tracker1' in info['tr']
        assert 'tracker2' in info['tr']
    
    def test_parse_magnet_link_minimal(self, plugin):
        """Test magnet link parsing with minimal info"""
        url = "magnet:?xt=urn:btih:example"
        
        info = plugin._parse_magnet_link(url)
        
        assert info['xt'] == 'urn:btih:example'
        assert info['dn'] == ''
        assert info['tr'] == []
    
    def test_extract_torrent_options_defaults(self, plugin, context):
        """Test torrent options extraction with defaults"""
        options = plugin._extract_torrent_options(context)
        
        assert options.max_connections == 50
        assert options.max_upload_slots == 8
        assert options.download_rate_limit == 0
        assert options.upload_rate_limit == 0
        assert options.seed_ratio == 0.0
        assert options.seed_time_limit == 0
        assert options.sequential_download is False
        assert options.prioritize_first_last is True
    
    def test_extract_torrent_options_custom(self, plugin, context):
        """Test torrent options extraction with custom values"""
        context.extra['torrent_max_connections'] = 100
        context.extra['torrent_max_upload_slots'] = 16
        context.extra['torrent_download_limit'] = 1024
        context.extra['torrent_upload_limit'] = 512
        context.extra['torrent_seed_ratio'] = 2.0
        context.extra['torrent_seed_time'] = 3600
        context.extra['torrent_sequential'] = True
        context.extra['torrent_prioritize_first_last'] = False
        
        options = plugin._extract_torrent_options(context)
        
        assert options.max_connections == 100
        assert options.max_upload_slots == 16
        assert options.download_rate_limit == 1024
        assert options.upload_rate_limit == 512
        assert options.seed_ratio == 2.0
        assert options.seed_time_limit == 3600
        assert options.sequential_download is True
        assert options.prioritize_first_last is False
    
    @pytest.mark.asyncio
    async def test_get_metadata_magnet(self, plugin, context):
        """Test getting metadata from magnet link"""
        url = "magnet:?xt=urn:btih:example"
        
        with patch('builtins.__import__'):
            with patch.object(plugin, '_get_magnet_metadata', new_callable=AsyncMock) as mock_metadata:
                mock_metadata.return_value = {
                    'name': 'Test',
                    'size': 1024,
                    'files': [],
                    'info_hash': 'abc123',
                    'trackers': [],
                }
                
                metadata = await plugin.get_metadata(url, context)
                
                assert metadata['name'] == 'Test'
                assert metadata['size'] == 1024
    
    @pytest.mark.asyncio
    async def test_get_metadata_torrent_file(self, plugin, context):
        """Test getting metadata from torrent file"""
        url = "http://example.com/file.torrent"
        
        with patch('builtins.__import__'):
            with patch.object(plugin, '_get_torrent_file_metadata', new_callable=AsyncMock) as mock_metadata:
                mock_metadata.return_value = {
                    'name': 'Test',
                    'size': 2048,
                    'files': [],
                    'info_hash': 'def456',
                    'trackers': [],
                }
                
                metadata = await plugin.get_metadata(url, context)
                
                assert metadata['name'] == 'Test'
                assert metadata['size'] == 2048
    
    @pytest.mark.asyncio
    async def test_get_metadata_failure(self, plugin, context):
        """Test getting metadata when it fails"""
        url = "magnet:?xt=urn:btih:example"
        
        with patch('builtins.__import__'):
            with patch.object(plugin, '_get_magnet_metadata', new_callable=AsyncMock) as mock_metadata:
                mock_metadata.side_effect = Exception("Failed")
                
                metadata = await plugin.get_metadata(url, context)
                
                assert metadata['name'] == ''
                assert metadata['size'] == 0


class TestTorrentOptions:
    """Test TorrentOptions dataclass"""
    
    def test_torrent_options_defaults(self):
        """Test torrent options with default values"""
        options = TorrentOptions()
        
        assert options.max_connections == 50
        assert options.max_upload_slots == 8
        assert options.download_rate_limit == 0
        assert options.upload_rate_limit == 0
        assert options.seed_ratio == 0.0
        assert options.seed_time_limit == 0
        assert options.sequential_download is False
        assert options.prioritize_first_last is True
    
    def test_torrent_options_custom(self):
        """Test torrent options with custom values"""
        options = TorrentOptions(
            max_connections=100,
            max_upload_slots=16,
            download_rate_limit=1024,
            upload_rate_limit=512,
            seed_ratio=2.0,
            seed_time_limit=3600,
            sequential_download=True,
            prioritize_first_last=False,
        )
        
        assert options.max_connections == 100
        assert options.max_upload_slots == 16
        assert options.download_rate_limit == 1024
        assert options.upload_rate_limit == 512
        assert options.seed_ratio == 2.0
        assert options.seed_time_limit == 3600
        assert options.sequential_download is True
        assert options.prioritize_first_last is False
