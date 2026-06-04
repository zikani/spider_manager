"""
Spider Manager — FTP Plugin
FTP protocol support plugin using aioftp
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from plugins.plugin_base import (
    SpiderPlugin,
    PluginCapability,
    PluginResult,
    PluginContext,
    PluginError,
    PluginAuthError,
    PluginNetworkError,
    DownloadMode,
)
from utils.logger import get_logger
from utils.url_parser import extract_filename

log = get_logger(__name__)


@dataclass
class FTPOptions:
    """FTP-specific download options"""
    username: Optional[str] = None
    password: Optional[str] = None
    passive_mode: bool = True
    use_tls: bool = False
    timeout: float = 30.0


class FTPPlugin(SpiderPlugin):
    """FTP protocol support plugin"""
    
    CAPABILITIES = PluginCapability.DIRECT_DOWNLOAD | PluginCapability.RESUMABLE
    
    def __init__(self):
        super().__init__()
        self._client = None
    
    @property
    def name(self) -> str:
        return "ftp"
    
    @property
    def description(self) -> str:
        return "FTP protocol downloader with authentication and resume support"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def author(self) -> str:
        return "Spider Manager Team"
    
    @property
    def capabilities(self) -> PluginCapability:
        return self.CAPABILITIES
    
    @property
    def priority(self) -> int:
        return 60  # Higher than default, lower than yt-dlp
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is FTP protocol"""
        try:
            parsed = urlparse(url)
            return parsed.scheme.lower() in ('ftp', 'ftps')
        except Exception:
            return False
    
    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        """
        Process FTP URL and return download descriptor.
        
        For FTP, we return a PluginResult with the direct FTP URL.
        The actual download will be handled by the download engine
        using aioftp for the transfer.
        """
        try:
            # Parse URL to extract components
            parsed = urlparse(url)
            
            # Extract filename from URL path
            filename = extract_filename(url)
            if not filename:
                filename = parsed.path.split('/')[-1] or "download"
            
            # Get file size from FTP server
            size = await self._get_file_size(url, ctx)
            
            # Build FTP options from context
            ftp_options = self._extract_ftp_options(url, ctx)
            
            # Store FTP options in context for download engine
            ctx.extra['ftp_options'] = ftp_options
            
            result = PluginResult(
                url=url,
                filename=filename,
                download_mode=DownloadMode.DIRECT,
                size=size,
                plugin_name=self.name,
            )
            
            log.info("[FTP] Processed URL: %s (size: %d bytes)", url, size)
            return result
            
        except Exception as exc:
            log.error("[FTP] Failed to process URL %s: %s", url, exc)
            raise PluginError(f"FTP processing failed: {exc}") from exc
    
    def _extract_ftp_options(self, url: str, ctx: PluginContext) -> FTPOptions:
        """Extract FTP options from URL and context"""
        parsed = urlparse(url)
        
        return FTPOptions(
            username=parsed.username or ctx.extra.get('ftp_username'),
            password=parsed.password or ctx.extra.get('ftp_password'),
            passive_mode=ctx.extra.get('ftp_passive', True),
            use_tls=parsed.scheme.lower() == 'ftps',
            timeout=ctx.extra.get('ftp_timeout', 30.0),
        )
    
    async def _get_file_size(self, url: str, ctx: PluginContext) -> int:
        """Get file size from FTP server"""
        try:
            import aioftp
            
            parsed = urlparse(url)
            options = self._extract_ftp_options(url, ctx)
            
            async with aioftp.Client.context(
                host=parsed.hostname,
                port=parsed.port or 21,
                username=options.username or "anonymous",
                password=options.password or "anonymous@",
                passive=options.passive_mode,
            ) as client:
                # Get file size using SIZE command
                size = await client.size(parsed.path)
                return size
                
        except ImportError:
            raise PluginError(
                "aioftp package is required for FTP support. "
                "Install it with: pip install aioftp>=0.21.0"
            )
        except Exception as exc:
            log.warning("[FTP] Could not get file size for %s: %s", url, exc)
            return 0  # Size unknown, download engine will handle it
    
    async def get_metadata(self, url: str, ctx: PluginContext) -> dict:
        """
        Get file metadata from FTP server.
        
        Returns:
            dict with keys: size, modified_time, is_directory
        """
        try:
            import aioftp
            
            parsed = urlparse(url)
            options = self._extract_ftp_options(url, ctx)
            
            async with aioftp.Client.context(
                host=parsed.hostname,
                port=parsed.port or 21,
                username=options.username or "anonymous",
                password=options.password or "anonymous@",
                passive=options.passive_mode,
            ) as client:
                # Try to get file info
                try:
                    stat = await client.stat(parsed.path)
                    return {
                        'size': stat.get('size', 0),
                        'modified_time': stat.get('modify', ''),
                        'is_directory': stat.get('type', 'file') == 'dir',
                    }
                except Exception:
                    # Fallback to size command
                    size = await client.size(parsed.path)
                    return {
                        'size': size,
                        'modified_time': '',
                        'is_directory': False,
                    }
                    
        except Exception as exc:
            log.error("[FTP] Failed to get metadata for %s: %s", url, exc)
            return {'size': 0, 'modified_time': '', 'is_directory': False}
    
    async def list_directory(self, url: str, ctx: PluginContext) -> list[dict]:
        """
        List files in FTP directory.
        
        Returns:
            list of dicts with keys: name, size, modified_time, is_directory
        """
        try:
            import aioftp
            
            parsed = urlparse(url)
            options = self._extract_ftp_options(url, ctx)
            
            async with aioftp.Client.context(
                host=parsed.hostname,
                port=parsed.port or 21,
                username=options.username or "anonymous",
                password=options.password or "anonymous@",
                passive=options.passive_mode,
            ) as client:
                # List directory contents
                files = []
                async for path, info in client.list(parsed.path or '/'):
                    files.append({
                        'name': Path(str(path)).name,
                        'size': info.get('size', 0),
                        'modified_time': info.get('modify', ''),
                        'is_directory': info.get('type', 'file') == 'dir',
                    })
                return files
                
        except Exception as exc:
            log.error("[FTP] Failed to list directory %s: %s", url, exc)
            raise PluginNetworkError(f"FTP directory listing failed: {exc}") from exc
    
    async def download_file(
        self,
        url: str,
        local_path: Path,
        ctx: PluginContext,
        resume: bool = False,
        progress_callback=None,
    ) -> Path:
        """
        Download file from FTP server to local path.
        
        Args:
            url: FTP URL
            local_path: Local file path to save to
            ctx: Plugin context
            resume: Whether to resume interrupted download
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file
        """
        try:
            import aioftp
            import aiofiles
            
            parsed = urlparse(url)
            options = self._extract_ftp_options(url, ctx)
            
            # Check if resuming
            start_pos = 0
            if resume and local_path.exists():
                start_pos = local_path.stat().st_size
                log.info("[FTP] Resuming download from byte %d", start_pos)
            
            async with aioftp.Client.context(
                host=parsed.hostname,
                port=parsed.port or 21,
                username=options.username or "anonymous",
                password=options.password or "anonymous@",
                passive=options.passive_mode,
            ) as client:
                # Open file for writing
                mode = 'ab' if resume else 'wb'
                async with aiofiles.open(local_path, mode) as f:
                    # Download with progress callback
                    async for block in client.download_stream(
                        parsed.path,
                        offset=start_pos,
                    ):
                        await f.write(block)
                        if progress_callback:
                            progress_callback(len(block))
                
                log.info("[FTP] Downloaded %s to %s", url, local_path)
                return local_path
                
        except ImportError:
            raise PluginError(
                "aioftp package is required for FTP support. "
                "Install it with: pip install aioftp>=0.21.0"
            )
        except Exception as exc:
            log.error("[FTP] Failed to download %s: %s", url, exc)
            raise PluginNetworkError(f"FTP download failed: {exc}") from exc
