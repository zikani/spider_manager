"""
Protocol Handler - Central registry for protocol-specific download handlers.
Supports HTTP, HTTPS, FTP, BitTorrent, and Magnet protocols.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

from utils.logger import get_logger

log = get_logger(__name__)


class UnsupportedProtocolError(ValueError):
    """Raised when a protocol is not supported."""
    pass


def normalize_url(url: str) -> str:
    """
    Normalize HTTP/HTTPS URL.
    For magnet and torrent URLs, return as-is after validation.
    Kept for backward compatibility.
    """
    u = url.strip()
    if not u:
        raise ValueError("URL is empty")
    parsed = urlparse(u)
    scheme = (parsed.scheme or "").lower()
    
    # Allow magnet and torrent schemes to pass through
    if scheme in ("magnet", "torrent"):
        return u
    
    if not parsed.scheme:
        u = "https://" + u
        parsed = urlparse(u)
        scheme = (parsed.scheme or "").lower()
    
    if scheme not in ("http", "https"):
        raise UnsupportedProtocolError(f"Only HTTP and HTTPS are supported (got {scheme!r})")
    netloc = parsed.netloc.lower()
    if not netloc:
        raise ValueError("URL has no host")
    normalized = urlunparse(
        (
            scheme,
            netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return normalized


class ProtocolHandler(ABC):
    """
    Abstract base class for protocol-specific download handlers.
    Each protocol (HTTP, HTTPS, FTP, BitTorrent, Magnet) should implement this.
    """

    @property
    @abstractmethod
    def protocol(self) -> str:
        """Protocol name (e.g., 'http', 'https', 'ftp', 'torrent', 'magnet')."""
        pass

    @property
    @abstractmethod
    def supported_schemes(self) -> list[str]:
        """List of URL schemes this handler supports."""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this handler can process the given URL."""
        pass

    @abstractmethod
    async def download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download file using this protocol.
        
        Args:
            url: The URL to download
            options: Download options (headers, referrer, etc.)
            
        Returns:
            Dict containing download result and metadata
        """
        pass

    def get_protocol_from_url(self, url: str) -> str:
        """Extract protocol scheme from URL."""
        parsed = urlparse(url)
        return parsed.scheme.lower() if parsed.scheme else ""


class ProtocolRegistry:
    """
    Central registry for protocol handlers.
    Manages protocol detection and routing to appropriate handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, ProtocolHandler] = {}

    def register(self, handler: ProtocolHandler) -> None:
        """Register a protocol handler."""
        for scheme in handler.supported_schemes:
            self._handlers[scheme] = handler
            log.info(f"Registered handler for protocol: {scheme}")

    def unregister(self, protocol: str) -> bool:
        """Unregister a protocol handler."""
        if protocol in self._handlers:
            del self._handlers[protocol]
            log.info(f"Unregistered handler for protocol: {protocol}")
            return True
        return False

    def get_handler(self, protocol: str) -> Optional[ProtocolHandler]:
        """Get handler for specific protocol."""
        return self._handlers.get(protocol.lower())

    def detect_protocol(self, url: str) -> str:
        """
        Detect protocol from URL.

        Returns:
            Protocol scheme (e.g., 'http', 'https', 'ftp', 'torrent', 'magnet')
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        # Handle magnet links (special case)
        if url.startswith("magnet:"):
            return "magnet"

        # Check URL scheme first - this takes precedence over file extension
        if scheme:
            return scheme

        # Only check for .torrent extension if there's no URL scheme
        # This allows HTTP/HTTPS URLs to .torrent files to work correctly
        if url.endswith(".torrent"):
            return "torrent"

        # Default to http if no scheme
        return "http"

    def get_handler_for_url(self, url: str) -> Optional[ProtocolHandler]:
        """
        Get appropriate handler for URL.
        
        Args:
            url: The URL to process
            
        Returns:
            ProtocolHandler instance or None if no handler found
        """
        protocol = self.detect_protocol(url)
        handler = self.get_handler(protocol)
        
        if not handler:
            log.warning(f"No handler found for protocol: {protocol}")
            return None
        
        if not handler.can_handle(url):
            log.warning(f"Handler {handler.protocol} cannot handle URL: {url}")
            return None
        
        return handler

    async def handle_download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route download to appropriate protocol handler with fallback support.
        
        Args:
            url: The URL to download
            options: Download options
            
        Returns:
            Dict containing download result
            
        Raises:
            UnsupportedProtocolError if no handler can handle the URL
        """
        handler = self.get_handler_for_url(url)
        
        if not handler:
            protocol = self.detect_protocol(url)
            # Try fallback to HTTP if HTTPS handler fails
            if protocol == "https" and self.is_protocol_supported("http"):
                log.info(f"HTTPS handler not available, falling back to HTTP handler")
                handler = self.get_handler("http")
                if handler:
                    # Convert HTTPS URL to HTTP for fallback
                    http_url = url.replace("https://", "http://", 1)
                    if handler.can_handle(http_url):
                        log.info(f"Attempting HTTP fallback for: {url}")
                        return await handler.download(http_url, options)
            
            raise UnsupportedProtocolError(f"No handler available for protocol: {protocol}")
        
        log.info(f"Routing {protocol}:// download to {handler.protocol} handler")
        
        try:
            return await handler.download(url, options)
        except Exception as e:
            log.warning(f"Handler {handler.protocol} failed for {url}: {e}")
            
            # Try fallback to HTTP if HTTPS handler fails
            if handler.protocol == "https" and self.is_protocol_supported("http"):
                log.info(f"HTTPS handler failed, falling back to HTTP handler")
                http_handler = self.get_handler("http")
                if http_handler:
                    http_url = url.replace("https://", "http://", 1)
                    if http_handler.can_handle(http_url):
                        log.info(f"Attempting HTTP fallback for: {url}")
                        return await http_handler.download(http_url, options)
            
            raise

    def get_supported_protocols(self) -> list[str]:
        """Return list of supported protocols."""
        return list(self._handlers.keys())

    def is_protocol_supported(self, protocol: str) -> bool:
        """Check if protocol is supported."""
        return protocol.lower() in self._handlers


# Global registry instance
_registry: Optional[ProtocolRegistry] = None


def get_protocol_registry() -> ProtocolRegistry:
    """Get global protocol registry instance."""
    global _registry
    if _registry is None:
        _registry = ProtocolRegistry()
    return _registry


class HTTPHandler(ProtocolHandler):
    """
    HTTP protocol handler.
    Handles HTTP downloads using the existing download engine infrastructure.
    """

    def __init__(self):
        self._download_engine = None

    @property
    def protocol(self) -> str:
        return "http"

    @property
    def supported_schemes(self) -> list[str]:
        return ["http"]

    def can_handle(self, url: str) -> bool:
        """Check if URL is HTTP protocol."""
        return url.lower().startswith("http://")

    async def download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download file via HTTP.
        
        Note: HTTP downloads are currently handled directly by DownloadEngine.
        This handler is reserved for future protocol-specific optimizations
        and will be integrated when the download engine is refactored to use
        the protocol handler architecture more extensively.
        """
        # HTTP downloads are handled by DownloadEngine.download()
        # This handler will be enhanced in future versions for protocol-specific features
        raise NotImplementedError(
            "HTTP downloads are currently handled by DownloadEngine. "
            "This handler will be integrated in a future refactoring."
        )


class HTTPSHandler(HTTPHandler):
    """
    HTTPS protocol handler.
    Extends HTTPHandler with SSL/TLS support.
    """

    @property
    def protocol(self) -> str:
        return "https"

    @property
    def supported_schemes(self) -> list[str]:
        return ["https"]

    def can_handle(self, url: str) -> bool:
        """Check if URL is HTTPS protocol."""
        return url.lower().startswith("https://")

    async def download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download file via HTTPS.
        
        Note: HTTPS downloads are currently handled directly by DownloadEngine.
        This handler is reserved for future protocol-specific optimizations
        and will be integrated when the download engine is refactored to use
        the protocol handler architecture more extensively.
        """
        # HTTPS downloads are handled by DownloadEngine.download()
        # This handler will be enhanced in future versions for protocol-specific features
        raise NotImplementedError(
            "HTTPS downloads are currently handled by DownloadEngine. "
            "This handler will be integrated in a future refactoring."
        )


class TorrentHandler(ProtocolHandler):
    """
    BitTorrent protocol handler.
    Handles .torrent file downloads using libtorrent.
    """

    @property
    def protocol(self) -> str:
        return "torrent"

    @property
    def supported_schemes(self) -> list[str]:
        return ["torrent"]

    def can_handle(self, url: str) -> bool:
        """Check if URL is a torrent file."""
        return url.lower().endswith(".torrent") or url.lower().startswith("torrent:")

    async def download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download file via BitTorrent.

        This is a placeholder that delegates to the TorrentPlugin.
        The actual download is handled by the download engine's _run_torrent method.
        """
        return {
            "url": url,
            "protocol": "torrent",
            "status": "pending",
            "message": "Torrent download handled by TorrentPlugin via download engine"
        }


class MagnetHandler(ProtocolHandler):
    """
    Magnet link protocol handler.
    Handles magnet: URIs using libtorrent.
    """

    @property
    def protocol(self) -> str:
        return "magnet"

    @property
    def supported_schemes(self) -> list[str]:
        return ["magnet"]

    def can_handle(self, url: str) -> bool:
        """Check if URL is a magnet link."""
        return url.lower().startswith("magnet:")

    async def download(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download file via magnet link.

        This is a placeholder that delegates to the TorrentPlugin.
        The actual download is handled by the download engine's _run_torrent method.
        """
        return {
            "url": url,
            "protocol": "magnet",
            "status": "pending",
            "message": "Magnet download handled by TorrentPlugin via download engine"
        }


def register_default_handlers(registry: ProtocolRegistry) -> None:
    """
    Register default protocol handlers (HTTP, HTTPS, Torrent, Magnet).
    """
    registry.register(HTTPHandler())
    registry.register(HTTPSHandler())
    registry.register(TorrentHandler())
    registry.register(MagnetHandler())
    log.info("Registered default protocol handlers: http, https, torrent, magnet")
