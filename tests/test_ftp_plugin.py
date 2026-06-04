"""
Unit tests for FTP Plugin
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from plugins.ftp_plugin import FTPPlugin, FTPOptions
from plugins.plugin_base import PluginContext, PluginError, PluginNetworkError


class TestFTPPlugin:
    """Test FTP plugin functionality"""
    
    @pytest.fixture
    def plugin(self):
        return FTPPlugin()
    
    @pytest.fixture
    def context(self):
        return PluginContext()
    
    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties"""
        assert plugin.name == "ftp"
        assert "FTP protocol" in plugin.description
        assert plugin.version == "1.0.0"
        assert plugin.author == "Spider Manager Team"
        assert plugin.priority == 60
    
    def test_can_handle_ftp_url(self, plugin):
        """Test FTP URL detection"""
        assert plugin.can_handle("ftp://example.com/file.txt") is True
        assert plugin.can_handle("ftps://example.com/file.txt") is True
        assert plugin.can_handle("FTP://EXAMPLE.COM/FILE.TXT") is True
        assert plugin.can_handle("http://example.com/file.txt") is False
        assert plugin.can_handle("https://example.com/file.txt") is False
    
    def test_can_handle_invalid_url(self, plugin):
        """Test URL detection with invalid URLs"""
        assert plugin.can_handle("not a url") is False
        assert plugin.can_handle("") is False
    
    @pytest.mark.asyncio
    async def test_process_ftp_url(self, plugin, context):
        """Test processing FTP URL"""
        url = "ftp://example.com/testfile.txt"
        
        with patch.object(plugin, '_get_file_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 1024
            
            result = await plugin.process(url, context)
            
            assert result.url == url
            assert result.filename == "testfile.txt"
            assert result.size == 1024
            assert result.plugin_name == "ftp"
            mock_size.assert_called_once_with(url, context)
    
    @pytest.mark.asyncio
    async def test_process_ftp_url_with_path(self, plugin, context):
        """Test processing FTP URL with path"""
        url = "ftp://example.com/path/to/file.zip"
        
        with patch.object(plugin, '_get_file_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 2048
            
            result = await plugin.process(url, context)
            
            assert result.filename == "file.zip"
            assert result.size == 2048
    
    @pytest.mark.asyncio
    async def test_process_ftp_url_with_credentials(self, plugin, context):
        """Test processing FTP URL with embedded credentials"""
        url = "ftp://user:pass@example.com/file.txt"
        
        with patch.object(plugin, '_get_file_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 512
            
            result = await plugin.process(url, context)
            
            assert 'ftp_options' in context.extra
            options = context.extra['ftp_options']
            assert isinstance(options, FTPOptions)
            assert options.username == "user"
            assert options.password == "pass"
    
    @pytest.mark.asyncio
    async def test_process_ftps_url(self, plugin, context):
        """Test processing FTPS URL (FTP over TLS)"""
        url = "ftps://example.com/file.txt"
        
        with patch.object(plugin, '_get_file_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 1024
            
            result = await plugin.process(url, context)
            
            assert 'ftp_options' in context.extra
            options = context.extra['ftp_options']
            assert options.use_tls is True
    
    @pytest.mark.asyncio
    async def test_extract_ftp_options(self, plugin, context):
        """Test FTP options extraction"""
        url = "ftp://user:pass@example.com:2121/file.txt"
        context.extra['ftp_passive'] = False
        context.extra['ftp_timeout'] = 60.0
        
        options = plugin._extract_ftp_options(url, context)
        
        assert options.username == "user"
        assert options.password == "pass"
        assert options.passive_mode is False
        assert options.timeout == 60.0
    
    @pytest.mark.asyncio
    async def test_extract_ftp_options_defaults(self, plugin, context):
        """Test FTP options extraction with defaults"""
        url = "ftp://example.com/file.txt"
        
        options = plugin._extract_ftp_options(url, context)
        
        assert options.username is None
        assert options.password is None
        assert options.passive_mode is True
        assert options.use_tls is False
        assert options.timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_get_file_size_success(self, plugin, context):
        """Test getting file size from FTP server"""
        url = "ftp://example.com/file.txt"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.size = AsyncMock(return_value=4096)
            mock_context.return_value.__aenter__.return_value = mock_client
            
            size = await plugin._get_file_size(url, context)
            
            assert size == 4096
            mock_client.size.assert_called_once_with("/file.txt")
    
    @pytest.mark.asyncio
    async def test_get_file_size_no_aioftp(self, plugin, context):
        """Test getting file size when aioftp is not installed"""
        url = "ftp://example.com/file.txt"
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'aioftp'")):
            with pytest.raises(PluginError, match="aioftp package is required"):
                await plugin._get_file_size(url, context)
    
    @pytest.mark.asyncio
    async def test_get_file_size_failure(self, plugin, context):
        """Test getting file size when server fails"""
        url = "ftp://example.com/file.txt"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.size = AsyncMock(side_effect=Exception("Connection failed"))
            mock_context.return_value.__aenter__.return_value = mock_client
            
            size = await plugin._get_file_size(url, context)
            
            # Should return 0 on failure (size unknown)
            assert size == 0
    
    @pytest.mark.asyncio
    async def test_get_metadata_success(self, plugin, context):
        """Test getting file metadata from FTP server"""
        url = "ftp://example.com/file.txt"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.stat = AsyncMock(return_value={
                'size': 8192,
                'modify': '20240101120000',
                'type': 'file'
            })
            mock_context.return_value.__aenter__.return_value = mock_client
            
            metadata = await plugin.get_metadata(url, context)
            
            assert metadata['size'] == 8192
            assert metadata['modified_time'] == '20240101120000'
            assert metadata['is_directory'] is False
    
    @pytest.mark.asyncio
    async def test_get_metadata_fallback(self, plugin, context):
        """Test getting metadata with fallback to size command"""
        url = "ftp://example.com/file.txt"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.stat = AsyncMock(side_effect=Exception("STAT not supported"))
            mock_client.size = AsyncMock(return_value=4096)
            mock_context.return_value.__aenter__.return_value = mock_client
            
            metadata = await plugin.get_metadata(url, context)
            
            assert metadata['size'] == 4096
            assert metadata['modified_time'] == ''
            assert metadata['is_directory'] is False
    
    @pytest.mark.asyncio
    async def test_list_directory_success(self, plugin, context):
        """Test listing FTP directory"""
        url = "ftp://example.com/"
        
        async def mock_list(path):
            yield Path('/file1.txt'), {'size': 1024, 'modify': '20240101120000', 'type': 'file'}
            yield Path('/file2.txt'), {'size': 2048, 'modify': '20240101130000', 'type': 'file'}
            yield Path('/subdir'), {'size': 0, 'modify': '20240101140000', 'type': 'dir'}
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.list = mock_list
            mock_context.return_value.__aenter__.return_value = mock_client
            
            files = await plugin.list_directory(url, context)
            
            assert len(files) == 3
            assert files[0]['name'] == 'file1.txt'
            assert files[0]['size'] == 1024
            assert files[0]['is_directory'] is False
            assert files[2]['name'] == 'subdir'
            assert files[2]['is_directory'] is True
    
    @pytest.mark.asyncio
    async def test_list_directory_failure(self, plugin, context):
        """Test listing directory when server fails"""
        url = "ftp://example.com/"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.list = AsyncMock(side_effect=Exception("Permission denied"))
            mock_context.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(PluginNetworkError, match="FTP directory listing failed"):
                await plugin.list_directory(url, context)
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, plugin, context, tmp_path):
        """Test downloading file from FTP server"""
        url = "ftp://example.com/file.txt"
        local_path = tmp_path / "file.txt"
        
        async def mock_download_stream(path, offset=0):
            yield b"Hello, World!"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.download_stream = mock_download_stream
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await plugin.download_file(url, local_path, context)
            
            assert result == local_path
            assert local_path.exists()
            assert local_path.read_text() == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_download_file_resume(self, plugin, context, tmp_path):
        """Test resuming interrupted download"""
        url = "ftp://example.com/file.txt"
        local_path = tmp_path / "file.txt"
        
        # Create partial file
        local_path.write_bytes(b"Hello, ")
        
        async def mock_download_stream(path, offset=0):
            assert offset == 7  # Should resume from byte 7
            yield b"World!"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.download_stream = mock_download_stream
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await plugin.download_file(url, local_path, context, resume=True)
            
            assert result == local_path
            assert local_path.read_text() == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_download_file_with_progress_callback(self, plugin, context, tmp_path):
        """Test downloading file with progress callback"""
        url = "ftp://example.com/file.txt"
        local_path = tmp_path / "file.txt"
        
        progress_updates = []
        
        def progress_callback(bytes_downloaded):
            progress_updates.append(bytes_downloaded)
        
        async def mock_download_stream(path, offset=0):
            yield b"Hello"
            yield b", "
            yield b"World!"
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.download_stream = mock_download_stream
            mock_context.return_value.__aenter__.return_value = mock_client
            
            await plugin.download_file(url, local_path, context, progress_callback=progress_callback)
            
            assert len(progress_updates) == 3
            assert all(p > 0 for p in progress_updates)
    
    @pytest.mark.asyncio
    async def test_download_file_no_aioftp(self, plugin, context, tmp_path):
        """Test downloading when aioftp is not installed"""
        url = "ftp://example.com/file.txt"
        local_path = tmp_path / "file.txt"
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'aioftp'")):
            with pytest.raises(PluginError, match="aioftp package is required"):
                await plugin.download_file(url, local_path, context)
    
    @pytest.mark.asyncio
    async def test_download_file_failure(self, plugin, context, tmp_path):
        """Test downloading when server fails"""
        url = "ftp://example.com/file.txt"
        local_path = tmp_path / "file.txt"
        
        async def mock_download_stream(path, offset=0):
            raise Exception("Connection lost")
        
        with patch('aioftp.Client.context') as mock_context:
            mock_client = AsyncMock()
            mock_client.download_stream = mock_download_stream
            mock_context.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(PluginNetworkError, match="FTP download failed"):
                await plugin.download_file(url, local_path, context)


class TestFTPOptions:
    """Test FTP options dataclass"""
    
    def test_ftp_options_defaults(self):
        """Test FTP options with default values"""
        options = FTPOptions()
        
        assert options.username is None
        assert options.password is None
        assert options.passive_mode is True
        assert options.use_tls is False
        assert options.timeout == 30.0
    
    def test_ftp_options_custom(self):
        """Test FTP options with custom values"""
        options = FTPOptions(
            username="testuser",
            password="testpass",
            passive_mode=False,
            use_tls=True,
            timeout=60.0,
        )
        
        assert options.username == "testuser"
        assert options.password == "testpass"
        assert options.passive_mode is False
        assert options.use_tls is True
        assert options.timeout == 60.0
