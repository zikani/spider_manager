"""
Spider Manager — BitTorrent Plugin
BitTorrent protocol support plugin using libtorrent
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from plugins.plugin_base import (
    SpiderPlugin,
    PluginCapability,
    PluginResult,
    PluginContext,
    PluginError,
    PluginDependencyMissing,
    DownloadMode,
)
from utils.logger import get_logger
from utils.url_parser import extract_filename

log = get_logger(__name__)


@dataclass
class TorrentOptions:
    """BitTorrent-specific download options"""
    max_connections: int = 50
    max_upload_slots: int = 8
    download_rate_limit: int = 0  # 0 = unlimited
    upload_rate_limit: int = 0  # 0 = unlimited
    seed_ratio: float = 0.0  # 0 = don't seed
    seed_time_limit: int = 0  # 0 = unlimited
    sequential_download: bool = False
    prioritize_first_last: bool = True


class TorrentPlugin(SpiderPlugin):
    """BitTorrent protocol support plugin"""
    
    CAPABILITIES = PluginCapability.DIRECT_DOWNLOAD | PluginCapability.RESUMABLE
    
    def __init__(self):
        super().__init__()
        self._session = None
    
    @property
    def name(self) -> str:
        return "torrent"
    
    @property
    def description(self) -> str:
        return "BitTorrent protocol downloader with magnet link and peer management support"
    
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
        return 55  # Higher than FTP, lower than yt-dlp
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is torrent or magnet link"""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme.lower() in ('magnet', 'torrent') or
                url.lower().endswith('.torrent') or
                parsed.path.lower().endswith('.torrent')
            )
        except Exception:
            return False
    
    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        """
        Process torrent/magnet URL and return download descriptor.
        
        For torrents, we return a PluginResult with the torrent URL.
        The actual download will be handled by the download engine
        using libtorrent for the transfer.
        """
        try:
            # Check if libtorrent is available
            self._check_libtorrent()
            
            # Parse URL to determine type
            if url.startswith('magnet:'):
                return await self._process_magnet(url, ctx)
            else:
                return await self._process_torrent_file(url, ctx)
                
        except PluginError:
            raise
        except Exception as exc:
            log.error("[Torrent] Failed to process URL %s: %s", url, exc)
            raise PluginError(f"Torrent processing failed: {exc}") from exc
    
    def _import_libtorrent(self):
        """Import libtorrent trying different possible package names"""
        import importlib
        lt = None
        # Try different possible import names for libtorrent
        for import_name in ['libtorrent', 'libtorrent_rasterbar']:
            try:
                lt = importlib.import_module(import_name)
                log.info(f"Successfully imported libtorrent as {import_name}")
                return lt
            except ImportError:
                continue
        
        return None
    
    def _check_libtorrent(self):
        """Check if libtorrent is available"""
        lt = self._import_libtorrent()
        if lt is None:
            raise PluginDependencyMissing(
                "libtorrent",
                install_hint="pip install python-libtorrent or pip install libtorrent"
            )
    
    async def _process_magnet(self, url: str, ctx: PluginContext) -> PluginResult:
        """Process magnet link"""
        try:
            lt = self._import_libtorrent()
            if lt is None:
                raise PluginDependencyMissing(
                    "libtorrent",
                    install_hint="pip install python-libtorrent or pip install libtorrent"
                )
            
            # Parse magnet link
            magnet_info = self._parse_magnet_link(url)
            
            # Create torrent session
            session = lt.session()
            settings = {
                'listen_interfaces': '0.0.0.0:6881',
                'enable_dht': True,
                'enable_lsd': True,
                'enable_upnp': True,
                'enable_natpmp': True,
            }
            session.apply_settings(settings)
            
            # Add magnet link
            handle = lt.add_magnet_uri(session, url, {'save_path': ctx.output_dir or '.'})
            
            # Wait for metadata to be downloaded
            timeout = 60  # seconds
            start_time = time.time()
            while not handle.has_metadata():
                await asyncio.sleep(1)
                if time.time() - start_time > timeout:
                    raise PluginError("Timeout waiting for torrent metadata")
            
            # Get torrent info
            torrent_info = handle.get_torrent_info()
            files = torrent_info.files()
            
            # Determine filename (use torrent name or first file)
            torrent_name = torrent_info.name()
            if files.num_files() == 1:
                filename = files.file_path(0).split('/')[-1]
            else:
                filename = torrent_name
            
            # Calculate total size
            total_size = torrent_info.total_size()
            
            # Build torrent options from context
            torrent_options = self._extract_torrent_options(ctx)
            ctx.extra['torrent_options'] = torrent_options
            
            result = PluginResult(
                url=url,
                filename=filename,
                download_mode=DownloadMode.TORRENT,
                size=total_size,
                plugin_name=self.name,
                title=torrent_name,
            )
            
            # If multiple files, mark as playlist
            if files.num_files() > 1:
                result.is_playlist = True
                result.playlist_title = torrent_name
                for i in range(files.num_files()):
                    file_path = files.file_path(i)
                    file_name = file_path.split('/')[-1]
                    file_size = files.file_size(i)
                    result.playlist_items.append(PluginResult(
                        url=url,
                        filename=file_name,
                        download_mode=DownloadMode.DIRECT,
                        size=file_size,
                        plugin_name=self.name,
                    ))
            
            log.info("[Torrent] Processed magnet: %s (size: %d bytes, files: %d)", 
                     torrent_name, total_size, files.num_files())
            return result
            
        except Exception as exc:
            log.error("[Torrent] Failed to process magnet link %s: %s", url, exc)
            raise PluginError(f"Magnet link processing failed: {exc}") from exc
    
    async def _process_torrent_file(self, url: str, ctx: PluginContext) -> PluginResult:
        """Process torrent file URL"""
        try:
            lt = self._import_libtorrent()
            if lt is None:
                raise PluginDependencyMissing(
                    "libtorrent",
                    install_hint="pip install python-libtorrent or pip install libtorrent"
                )
            
            # For torrent files, we need to download them first
            # This is a simplified version - in production, you'd download the .torrent file
            # and then parse it. For now, we'll return the URL and let the download engine handle it.
            
            filename = extract_filename(url)
            if not filename or not filename.endswith('.torrent'):
                filename = "download.torrent"
            
            # Build torrent options from context
            torrent_options = self._extract_torrent_options(ctx)
            ctx.extra['torrent_options'] = torrent_options
            
            result = PluginResult(
                url=url,
                filename=filename,
                download_mode=DownloadMode.TORRENT,
                size=0,  # Size unknown until torrent is parsed
                plugin_name=self.name,
            )
            
            log.info("[Torrent] Processed torrent file: %s", url)
            return result
            
        except Exception as exc:
            log.error("[Torrent] Failed to process torrent file %s: %s", url, exc)
            raise PluginError(f"Torrent file processing failed: {exc}") from exc
    
    def _parse_magnet_link(self, magnet_url: str) -> dict:
        """Parse magnet link components"""
        parsed = urlparse(magnet_url)
        params = parse_qs(parsed.query)
        
        return {
            'xt': params.get('xt', [''])[0],  # Exact topic (info hash)
            'dn': params.get('dn', [''])[0],  # Display name
            'tr': params.get('tr', []),       # Trackers
            'ws': params.get('ws', []),       # Web seeds
            'xs': params.get('xs', []),       # Exact source
        }
    
    def _extract_torrent_options(self, ctx: PluginContext) -> TorrentOptions:
        """Extract torrent options from context"""
        return TorrentOptions(
            max_connections=ctx.extra.get('torrent_max_connections', 50),
            max_upload_slots=ctx.extra.get('torrent_max_upload_slots', 8),
            download_rate_limit=ctx.extra.get('torrent_download_limit', 0),
            upload_rate_limit=ctx.extra.get('torrent_upload_limit', 0),
            seed_ratio=ctx.extra.get('torrent_seed_ratio', 0.0),
            seed_time_limit=ctx.extra.get('torrent_seed_time', 0),
            sequential_download=ctx.extra.get('torrent_sequential', False),
            prioritize_first_last=ctx.extra.get('torrent_prioritize_first_last', True),
        )
    
    async def get_metadata(self, url: str, ctx: PluginContext) -> dict:
        """
        Get torrent metadata.
        
        Returns:
            dict with keys: name, size, files, info_hash, trackers
        """
        try:
            lt = self._import_libtorrent()
            if lt is None:
                return {'name': '', 'size': 0, 'files': [], 'info_hash': '', 'trackers': []}
            
            if url.startswith('magnet:'):
                return await self._get_magnet_metadata(url, ctx)
            else:
                return await self._get_torrent_file_metadata(url, ctx)
                
        except Exception as exc:
            log.error("[Torrent] Failed to get metadata for %s: %s", url, exc)
            return {'name': '', 'size': 0, 'files': [], 'info_hash': '', 'trackers': []}
    
    async def _get_magnet_metadata(self, url: str, ctx: PluginContext) -> dict:
        """Get metadata from magnet link"""
        try:
            lt = self._import_libtorrent()
            if lt is None:
                return {'name': '', 'size': 0, 'files': [], 'info_hash': '', 'trackers': []}
            
            session = lt.session()
            settings = {
                'listen_interfaces': '0.0.0.0:6881',
                'enable_dht': True,
                'enable_lsd': True,
            }
            session.apply_settings(settings)
            
            handle = lt.add_magnet_uri(session, url, {'save_path': ctx.output_dir or '.'})
            
            # Wait for metadata
            timeout = 60
            start_time = time.time()
            while not handle.has_metadata():
                await asyncio.sleep(1)
                if time.time() - start_time > timeout:
                    raise PluginError("Timeout waiting for torrent metadata")
            
            torrent_info = handle.get_torrent_info()
            files = torrent_info.files()
            
            file_list = []
            for i in range(files.num_files()):
                file_list.append({
                    'path': files.file_path(i),
                    'size': files.file_size(i),
                })
            
            return {
                'name': torrent_info.name(),
                'size': torrent_info.total_size(),
                'files': file_list,
                'info_hash': str(torrent_info.info_hash()),
                'trackers': list(handle.trackers()),
            }
            
        except Exception as exc:
            log.error("[Torrent] Failed to get magnet metadata: %s", exc)
            raise PluginError(f"Failed to get magnet metadata: {exc}") from exc
    
    async def _get_torrent_file_metadata(self, url: str, ctx: PluginContext) -> dict:
        """Get metadata from torrent file"""
        try:
            lt = self._import_libtorrent()
            if lt is None:
                return {'name': '', 'size': 0, 'files': [], 'info_hash': '', 'trackers': []}
            
            # For torrent files, we'd need to download and parse them
            # This is a placeholder - in production, download the file first
            return {
                'name': '',
                'size': 0,
                'files': [],
                'info_hash': '',
                'trackers': [],
            }
            
        except Exception as exc:
            log.error("[Torrent] Failed to get torrent file metadata: %s", exc)
            raise PluginError(f"Failed to get torrent file metadata: {exc}") from exc
    
    async def download_torrent(
        self,
        url: str,
        save_path: Path,
        ctx: PluginContext,
        progress_callback=None,
    ) -> Path:
        """
        Download torrent using libtorrent.
        
        Args:
            url: Magnet link or torrent file URL
            save_path: Directory to save files
            ctx: Plugin context
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded files
        """
        try:
            lt = self._import_libtorrent()
            if lt is None:
                raise PluginDependencyMissing(
                    "libtorrent",
                    install_hint="pip install python-libtorrent or pip install libtorrent"
                )
            
            options = self._extract_torrent_options(ctx)
            
            # Create session
            session = lt.session()
            settings = {
                'listen_interfaces': '0.0.0.0:6881',
                'enable_dht': True,
                'enable_lsd': True,
                'enable_upnp': True,
                'enable_natpmp': True,
                'connections_limit': options.max_connections,
                'upload_slots_limit': options.max_upload_slots,
            }
            if options.download_rate_limit > 0:
                settings['download_rate_limit'] = options.download_rate_limit * 1024
            if options.upload_rate_limit > 0:
                settings['upload_rate_limit'] = options.upload_rate_limit * 1024
            session.apply_settings(settings)
            
            # Add torrent
            if url.startswith('magnet:'):
                handle = lt.add_magnet_uri(session, url, {'save_path': str(save_path)})
            else:
                # For torrent files, load from file
                handle = lt.add_torrent({'save_path': str(save_path), 'ti': lt.torrent_info(url)})
            
            # Set download priorities
            if options.prioritize_first_last:
                self._prioritize_first_last(handle)
            
            if options.sequential_download:
                handle.set_sequential_download(True)
            
            # Download loop
            while not handle.is_seed():
                await asyncio.sleep(1)
                
                status = handle.status()
                
                if progress_callback:
                    progress_callback({
                        'total': status.total_wanted,
                        'downloaded': status.total_wanted_done,
                        'download_rate': status.download_rate,
                        'upload_rate': status.upload_rate,
                        'progress': status.progress * 100,
                        'num_peers': status.num_peers,
                        'num_seeds': status.num_seeds,
                    })
                
                # Check seed ratio/time limits
                if options.seed_ratio > 0 and status.all_time_download > 0:
                    ratio = status.all_time_upload / status.all_time_download
                    if ratio >= options.seed_ratio:
                        log.info("[Torrent] Seed ratio reached: %.2f", ratio)
                        break
                
                if options.seed_time_limit > 0 and status.active_time >= options.seed_time_limit:
                    log.info("[Torrent] Seed time limit reached: %d seconds", options.seed_time_limit)
                    break
            
            log.info("[Torrent] Download completed: %s", url)
            return save_path
            
        except Exception as exc:
            log.error("[Torrent] Failed to download %s: %s", url, exc)
            raise PluginError(f"Torrent download failed: {exc}") from exc
    
    def _prioritize_first_last(self, handle):
        """Prioritize first and last pieces for preview"""
        try:
            torrent_info = handle.get_torrent_info()
            file_storage = torrent_info.files()
            
            # Prioritize first 5% and last 5% of each file
            for i in range(file_storage.num_files()):
                file_size = file_storage.file_size(i)
                first_piece = int(file_size * 0.05 / torrent_info.piece_length())
                last_piece = int(file_size * 0.95 / torrent_info.piece_length())
                
                # Set priority to 7 (highest)
                for piece in range(first_piece, last_piece + 1):
                    handle.piece_priority(piece, 7)
                    
        except Exception as exc:
            log.warning("[Torrent] Failed to set piece priorities: %s", exc)
