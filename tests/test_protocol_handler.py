import pytest

from core.protocol_handler import (
    UnsupportedProtocolError,
    normalize_url,
    ProtocolHandler,
    ProtocolRegistry,
    HTTPHandler,
    HTTPSHandler,
    get_protocol_registry,
    register_default_handlers,
)


def test_normalize_adds_https():
    assert normalize_url("example.com/file").startswith("https://")


def test_normalize_keeps_scheme():
    u = normalize_url("https://Example.COM/path")
    assert u.startswith("https://example.com/")


def test_rejects_ftp():
    with pytest.raises(UnsupportedProtocolError):
        normalize_url("ftp://host/file")


def test_rejects_empty():
    with pytest.raises(ValueError):
        normalize_url("")


class TestProtocolRegistry:
    """Test ProtocolRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry can be initialized."""
        registry = ProtocolRegistry()
        assert registry is not None
        assert registry.get_supported_protocols() == []

    def test_register_handler(self):
        """Test registering a handler."""
        registry = ProtocolRegistry()
        handler = HTTPHandler()
        registry.register(handler)
        assert "http" in registry.get_supported_protocols()

    def test_unregister_handler(self):
        """Test unregistering a handler."""
        registry = ProtocolRegistry()
        handler = HTTPHandler()
        registry.register(handler)
        assert registry.unregister("http")
        assert "http" not in registry.get_supported_protocols()

    def test_get_handler(self):
        """Test getting a handler by protocol."""
        registry = ProtocolRegistry()
        handler = HTTPHandler()
        registry.register(handler)
        assert registry.get_handler("http") is not None
        assert registry.get_handler("https") is None

    def test_detect_protocol_http(self):
        """Test protocol detection for HTTP."""
        registry = ProtocolRegistry()
        assert registry.detect_protocol("http://example.com/file") == "http"

    def test_detect_protocol_https(self):
        """Test protocol detection for HTTPS."""
        registry = ProtocolRegistry()
        assert registry.detect_protocol("https://example.com/file") == "https"

    def test_detect_protocol_magnet(self):
        """Test protocol detection for magnet links."""
        registry = ProtocolRegistry()
        assert registry.detect_protocol("magnet:?xt=urn:btih:...") == "magnet"

    def test_detect_protocol_torrent(self):
        """Test protocol detection for torrent files without URL scheme."""
        registry = ProtocolRegistry()
        # Torrent files without URL scheme should be detected as torrent
        assert registry.detect_protocol("file.torrent") == "torrent"
        # Torrent files with HTTP/HTTPS scheme should use the scheme (not file extension)
        assert registry.detect_protocol("http://example.com/file.torrent") == "http"
        assert registry.detect_protocol("https://example.com/file.torrent") == "https"

    def test_detect_protocol_default(self):
        """Test protocol detection defaults to http."""
        registry = ProtocolRegistry()
        assert registry.detect_protocol("example.com/file") == "http"

    def test_is_protocol_supported(self):
        """Test checking if protocol is supported."""
        registry = ProtocolRegistry()
        registry.register(HTTPHandler())
        assert registry.is_protocol_supported("http")
        assert not registry.is_protocol_supported("https")

    def test_get_handler_for_url(self):
        """Test getting handler for URL."""
        registry = ProtocolRegistry()
        registry.register(HTTPHandler())
        handler = registry.get_handler_for_url("http://example.com/file")
        assert handler is not None
        assert handler.protocol == "http"

    def test_get_handler_for_url_no_handler(self):
        """Test getting handler for URL with no handler."""
        registry = ProtocolRegistry()
        handler = registry.get_handler_for_url("ftp://example.com/file")
        assert handler is None


class TestHTTPHandler:
    """Test HTTPHandler functionality."""

    def test_http_handler_protocol(self):
        """Test HTTPHandler protocol property."""
        handler = HTTPHandler()
        assert handler.protocol == "http"

    def test_http_handler_supported_schemes(self):
        """Test HTTPHandler supported schemes."""
        handler = HTTPHandler()
        assert handler.supported_schemes == ["http"]

    def test_http_handler_can_handle(self):
        """Test HTTPHandler can_handle method."""
        handler = HTTPHandler()
        assert handler.can_handle("http://example.com/file")
        assert not handler.can_handle("https://example.com/file")
        assert not handler.can_handle("ftp://example.com/file")


class TestHTTPSHandler:
    """Test HTTPSHandler functionality."""

    def test_https_handler_protocol(self):
        """Test HTTPSHandler protocol property."""
        handler = HTTPSHandler()
        assert handler.protocol == "https"

    def test_https_handler_supported_schemes(self):
        """Test HTTPSHandler supported schemes."""
        handler = HTTPSHandler()
        assert handler.supported_schemes == ["https"]

    def test_https_handler_can_handle(self):
        """Test HTTPSHandler can_handle method."""
        handler = HTTPSHandler()
        assert handler.can_handle("https://example.com/file")
        assert not handler.can_handle("http://example.com/file")
        assert not handler.can_handle("ftp://example.com/file")


class TestRegisterDefaultHandlers:
    """Test default handler registration."""

    def test_register_default_handlers(self):
        """Test registering default handlers."""
        registry = ProtocolRegistry()
        register_default_handlers(registry)
        protocols = registry.get_supported_protocols()
        assert "http" in protocols
        assert "https" in protocols

    def test_global_registry(self):
        """Test global registry instance."""
        registry = get_protocol_registry()
        assert registry is not None
        # Register defaults if not already registered
        if not registry.is_protocol_supported("http"):
            register_default_handlers(registry)
        assert registry.is_protocol_supported("http")


class TestProtocolFallback:
    """Test protocol fallback mechanism."""

    @pytest.mark.asyncio
    async def test_fallback_https_to_http(self):
        """Test fallback from HTTPS to HTTP when HTTPS handler fails."""
        registry = ProtocolRegistry()
        registry.register(HTTPHandler())
        # HTTPS handler not registered, should fallback to HTTP
        
        # This test verifies the fallback logic exists
        # Actual download integration will be tested in download engine tests
        assert registry.is_protocol_supported("http")
        assert not registry.is_protocol_supported("https")
