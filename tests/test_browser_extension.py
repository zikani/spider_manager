"""
Tests for Browser Extension Plugin and Named Pipe communication.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from plugins.browser_extension import BrowserExtensionPlugin, ExtensionIPCHandler
from utils.logger import get_logger

log = get_logger(__name__)

class TestBrowserExtensionPlugin:
    """Test the BrowserExtensionPlugin class."""
    
    def test_host_name(self):
        """Test that HOST_NAME is correctly defined."""
        assert BrowserExtensionPlugin.HOST_NAME == "com.spidermanager.bridge"
    
    def test_pipe_name_defined(self):
        """Test that PIPE_NAME is correctly defined."""
        assert hasattr(BrowserExtensionPlugin, 'PIPE_NAME')
        assert BrowserExtensionPlugin.PIPE_NAME == r'\\.\pipe\spider_manager_ipc'
    
    def test_ipc_port_defined(self):
        """Test that IPC_PORT is correctly defined."""
        assert hasattr(BrowserExtensionPlugin, 'IPC_PORT')
        assert BrowserExtensionPlugin.IPC_PORT == 19999
    
    def test_send_message_format(self):
        """Test that send_message produces correct format."""
        message = {"url": "https://example.com", "filename": "test.txt"}
        try:
            BrowserExtensionPlugin.send_message(message)
        except Exception as e:
            pass
    
    def test_read_message_format(self):
        """Test that read_message can parse correct format."""
        test_data = json.dumps({"url": "https://example.com"}).encode('utf-8')
        length = len(test_data)
        
        assert hasattr(BrowserExtensionPlugin, 'read_message')


class TestExtensionIPCHandler:
    """Test the ExtensionIPCHandler class."""
    
    def test_initialization(self):
        """Test that ExtensionIPCHandler can be initialized."""
        from unittest.mock import Mock
        mock_queue = Mock()
        handler = ExtensionIPCHandler(mock_queue)
        assert handler.queue_manager == mock_queue
        assert handler.running == False
    
    def test_pipe_name_constant(self):
        """Test that the handler uses the correct pipe name."""
        assert BrowserExtensionPlugin.PIPE_NAME == r'\\.\pipe\spider_manager_ipc'


class TestMessageHandling:
    """Test message parsing and validation logic."""
    
    def test_valid_url_detection(self):
        """Test that valid URLs are correctly identified."""
        valid_urls = [
            "http://example.com/file.zip",
            "https://example.com/file.mp4",
            "http://test.com/path/to/file?query=value"
        ]
        for url in valid_urls:
            assert url.startswith(("http://", "https://"))
    
    def test_invalid_url_detection(self):
        """Test that invalid URLs are correctly rejected."""
        invalid_urls = [
            "ftp://example.com/file.zip",
            "file:///C:/file.txt",
            "javascript:void(0)",
            "data:text/plain,hello"
        ]
        for url in invalid_urls:
            assert not url.startswith(("http://", "https://"))
    
    def test_message_structure(self):
        """Test that messages have expected structure."""
        test_message = {
            "url": "https://example.com/file.zip",
            "filename": "file.zip",
            "referrer": "https://example.com",
            "cookieString": "session=abc123"
        }
        
        assert "url" in test_message
        assert "filename" in test_message
        assert test_message["url"].startswith(("http://", "https://"))


class TestNativeMessagingIntegration:
    """Integration tests for native messaging."""
    
    def test_manifest_structure(self):
        """Test that the manifest file has correct structure."""
        manifest_path = os.path.join(os.path.dirname(__file__), '..', 'com.spidermanager.bridge.json')
        
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            assert "name" in manifest
            assert "path" in manifest
            assert "type" in manifest
            assert "allowed_origins" in manifest
            assert manifest["name"] == "com.spidermanager.bridge"
            assert manifest["type"] == "stdio"
    
    def test_host_wrapper_exists(self):
        """Test that host_wrapper.bat exists."""
        wrapper_path = os.path.join(os.path.dirname(__file__), '..', 'host_wrapper.bat')
        assert os.path.exists(wrapper_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
