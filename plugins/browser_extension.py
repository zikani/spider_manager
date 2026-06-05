"""
BrowserExtensionPlugin - Handles communication with the browser extension.
"""

import json
import struct
import sys
import asyncio
import socket
import os
import time
from typing import Optional

try:
    import win32pipe
    import win32file
    import pywintypes
except ImportError:
    win32pipe = None
    win32file = None
    pywintypes = None

from plugins.plugin_base import SpiderPlugin, PluginResult, PluginContext, PluginCapability, PluginError
from utils.logger import get_logger

log = get_logger(__name__)

class BrowserExtensionPlugin(SpiderPlugin):
    HOST_NAME = "com.spidermanager.bridge"
    IPC_PORT = 19999
    PIPE_NAME = r'\\.\pipe\spider_manager_ipc'

    @property
    def name(self) -> str:
        return "browser-extension"

    @property
    def description(self) -> str:
        return "Handles automatic browser capture via Chrome/Firefox extension."

    @property
    def priority(self) -> int:
        return 10

    @property
    def capabilities(self) -> PluginCapability:
        return PluginCapability.NONE

    def can_handle(self, url: str) -> bool:
        """
        Browser extension plugin handles all URL types for interception.
        The actual processing is delegated to the appropriate plugin via the registry.
        """
        if not url:
            return False
        url_lower = url.lower()
        return (
            url_lower.startswith(('http://', 'https://', 'ftp://', 'ftps://', 'magnet:', 'torrent:')) or
            url_lower.endswith('.torrent')
        )

    async def process(self, url: str, ctx: PluginContext) -> PluginResult:
        raise PluginError("BrowserExtensionPlugin does not support direct processing.")

    @staticmethod
    def send_message(message: dict):
        encoded_message = json.dumps(message).encode('utf-8')
        sys.stdout.buffer.write(struct.pack('I', len(encoded_message)))
        sys.stdout.buffer.write(encoded_message)
        sys.stdout.buffer.flush()

    @staticmethod
    def read_message() -> Optional[dict]:
        text_length_bytes = sys.stdin.buffer.read(4)
        if not text_length_bytes:
            return None
        text_length = struct.unpack('I', text_length_bytes)[0]
        message_bytes = sys.stdin.buffer.read(text_length)
        if not message_bytes:
            return None
        return json.loads(message_bytes.decode('utf-8'))

    @classmethod
    def run_as_host(cls):
        """Entry point for the native messaging host."""
        log_dir = os.path.expanduser("~/.spider_manager")
        os.makedirs(log_dir, exist_ok=True)
        sys.stderr = open(os.path.join(log_dir, "host.log"), "a")
        sys.stderr.write(f"\n=== Native Host Started at {time.time()} ===\n")
        sys.stderr.flush()
        
        try:
            while True:
                message = cls.read_message()
                if message is None:
                    sys.stderr.write("No more messages, exiting\n")
                    sys.stderr.flush()
                    break
                
                sys.stderr.write(f"Received from browser: {message}\n")
                sys.stderr.flush()
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2.0)
                        s.connect(('127.0.0.1', cls.IPC_PORT))
                        s.sendall(json.dumps(message).encode('utf-8'))
                        sys.stderr.write(f"Successfully forwarded to app on port {cls.IPC_PORT}\n")
                except ConnectionRefusedError:
                    sys.stderr.write(f"ERROR: Connection refused - Spider Manager not running on port {cls.IPC_PORT}\n")
                    sys.stderr.write("Please start Spider Manager application to enable download interception.\n")
                except socket.timeout:
                    sys.stderr.write(f"ERROR: Connection timeout to port {cls.IPC_PORT}\n")
                    sys.stderr.write("Spider Manager may be busy or not responding.\n")
                except OSError as e:
                    sys.stderr.write(f"ERROR: Network error connecting to port {cls.IPC_PORT}: {e}\n")
                except Exception as e:
                    sys.stderr.write(f"ERROR: Unexpected socket error: {e}\n")
                
                sys.stderr.flush()
                cls.send_message({"status": "received", "url": message.get("url")})
        except Exception as e:
            sys.stderr.write(f"Native Messaging Host error: {e}\n")
            sys.stderr.flush()
        finally:
            sys.stderr.write("=== Native Host Stopped ===\n")
            sys.stderr.flush()

class ExtensionIPCHandler:
    """Server inside the main app to receive messages from the native host."""
    def __init__(self, queue_manager, dialog_callback=None):
        self.queue_manager = queue_manager
        self.server = None
        self.dialog_callback = dialog_callback
        self.detected_streams = {}
    
    @staticmethod
    def is_streaming_url(url: str) -> bool:
        """Detect if URL is a streaming media URL (HLS, DASH, etc.)."""
        if not url:
            return False
        url_lower = url.lower()
        streaming_indicators = [
            '.m3u8', '.m3u',
            '.mpd',
            '.f4m',
            'blob:',
            'manifest',
            'master.m3u8',
            'playlist.m3u8',
            'googlevideo.com',
            'videoplayback',
        ]
        return any(indicator in url_lower for indicator in streaming_indicators)

    async def start(self):
        try:
            self.server = await asyncio.start_server(
                self.handle_client, '127.0.0.1', BrowserExtensionPlugin.IPC_PORT
            )
            log.info(f"Extension IPC Server started on port {BrowserExtensionPlugin.IPC_PORT}")
        except OSError as e:
            log.error(f"Failed to start IPC server on port {BrowserExtensionPlugin.IPC_PORT}: {e}")
            log.error("Browser extension download interception will not work.")
            log.error("Check if another application is using this port.")
            raise

    async def handle_client(self, reader, writer):
        try:
            data = await reader.read(8192)
            if not data:
                log.debug("No data received from extension client")
                return

            try:
                message = json.loads(data.decode('utf-8'))
                log.debug(f"Received message from extension: {message}")
            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON received from extension: {e}")
                return

            msg_type = message.get("type")

            if msg_type == "GET_QUALITIES":
                response = await self._handle_get_qualities(message.get("url"))
                await self._send_response(writer, response)
                return

            if msg_type == "GET_QUEUE_STATUS":
                response = self._handle_get_queue_status()
                await self._send_response(writer, response)
                return

            if msg_type == "CLEAR_HISTORY":
                response = {"ok": True}
                await self._send_response(writer, response)
                return

            if msg_type == "CANCEL_ITEM":
                response = self._handle_cancel_item(message.get("id"))
                await self._send_response(writer, response)
                return

            if msg_type == "GET_STREAM_INFO":
                url = message.get("url")
                info = self.detected_streams.get(url)
                response = {"info": info}
                await self._send_response(writer, response)
                return

            if msg_type == "STREAM_MANIFEST_DETECTED":
                self._handle_stream_manifest_detected(message)
                await self._send_response(writer, {"ok": True})
                return

            if msg_type in ("DOWNLOAD", "DOWNLOAD_HIGH") or message.get("action") == "download" or "url" in message:
                url = message.get("url")

                if url and url.startswith("blob:"):
                    original_url = message.get("originalUrl") or message.get("pageTitle") or ""
                    if original_url and original_url.startswith(("http://", "https://")):
                        log.info(f"Blob URL detected, using page URL for yt-dlp: {original_url}")
                        url = original_url
                        message["fallbackYtdlp"] = True
                    else:
                        log.error(f"Blob URL without valid page URL fallback: {url}")
                        return

                if not url or not isinstance(url, str):
                    log.error(f"Invalid URL received from extension: {url}")
                    return
                
                # Decode HTML entities (e.g., &amp; -> &) that may be present in magnet links
                import html
                url = html.unescape(url)
                
                # Accept HTTP, HTTPS, FTP, FTPS, magnet, and torrent URLs
                url_lower = url.lower()
                valid_schemes = ('http://', 'https://', 'ftp://', 'ftps://', 'magnet:', 'torrent:')
                if not (url_lower.startswith(valid_schemes) or url_lower.endswith('.torrent')):
                    log.error(f"Invalid URL scheme received from extension: {url}")
                    return

                from utils.url_parser import safe_filename_from_url, is_valid_url
                from config.settings import get_download_directory

                # Skip URL validation for magnet links (they're not HTTP/HTTPS)
                if not url_lower.startswith('magnet:'):
                    if not is_valid_url(url):
                        log.error(f"URL validation failed: {url}")
                        return

                filename = message.get("filename") or safe_filename_from_url(url)
                referrer = message.get("referrer", "")
                cookie_string = message.get("cookieString")
                stream_type = message.get("streamType", "")
                download_mode = message.get("downloadMode", "")
                blob_url = message.get("blobUrl", "")
                content_type = message.get("contentType", "")
                fallback_ytdlp = message.get("fallbackYtdlp", False)
                priority = "high" if msg_type == "DOWNLOAD_HIGH" else "normal"
                
                headers = {}
                if cookie_string:
                    headers["Cookie"] = cookie_string
                if referrer:
                    headers["Referer"] = referrer
                
                request_headers = message.get("requestHeaders", {})
                if request_headers:
                    important_headers = [
                        "user-agent", "accept", "accept-language", "accept-encoding",
                        "authorization", "x-requested-with", "origin", "sec-fetch-*"
                    ]
                    for key, value in request_headers.items():
                        if any(pattern in key.lower() for pattern in important_headers) or key.lower() not in headers:
                            headers[key] = value
                
                response_headers = message.get("responseHeaders", {})
                if response_headers:
                    auth_headers = ["www-authenticate", "set-cookie", "authorization"]
                    for key, value in response_headers.items():
                        if any(pattern in key.lower() for pattern in auth_headers):
                            headers[f"response-{key}"] = value

                is_streaming = stream_type in ("hls", "dash", "blob") or self.is_streaming_url(url)

                use_ytdlp = (
                    fallback_ytdlp or
                    download_mode in ("blob", "ytdlp") or
                    stream_type in ("blob",) or
                    (stream_type in ("hls", "dash") and download_mode in ("stream_hls", "stream_dash"))
                )

                download_info = {
                    "url": url,
                    "filename": filename,
                    "referrer": referrer,
                    "cookie_string": cookie_string,
                    "save_path": get_download_directory(),
                    "headers": headers,
                    "request_headers": request_headers,
                    "response_headers": response_headers,
                    "method": message.get("method", "GET"),
                    "status_code": message.get("statusCode"),
                    "is_streaming": is_streaming,
                    "stream_type": stream_type,
                    "download_mode": download_mode,
                    "blob_url": blob_url,
                    "content_type": content_type,
                    "priority": priority,
                    "use_ytdlp": use_ytdlp,
                }

                hls_info = message.get("hlsInfo")
                if hls_info:
                    download_info["hls_info"] = hls_info
                    download_info["is_streaming"] = True
                    self.detected_streams[url] = {"type": "hls", "info": hls_info}
                    log.info(f"HLS stream detected with {len(hls_info.get('variants', []))} variants")
                    for variant in hls_info.get('variants', []):
                        log.debug(f"  Variant: {variant.get('resolution', 'unknown')} @ {variant.get('bandwidthMbps', 'N/A')} Mbps")

                video_info = message.get("videoInfo")
                if video_info:
                    download_info["video_info"] = video_info
                    platform = video_info.get('platform', 'unknown')
                    video_stream_type = video_info.get('type', 'unknown')
                    download_info["is_streaming"] = True
                    self.detected_streams[url] = {"type": video_stream_type, "info": video_info}
                    log.info(f"Video stream detected on platform: {platform}, type: {video_stream_type}")
                    if 'qualities' in video_info:
                        log.info(f"  Available qualities: {[q.get('label') for q in video_info['qualities']]}")

                if self.dialog_callback:
                    log.info(f"Triggering download dialog for: {filename} (priority: {priority})")
                    self.dialog_callback(download_info)
                else:
                    try:
                        task = self.queue_manager.create_task(
                            url=url,
                            filename=filename,
                            save_path=get_download_directory(),
                            referrer=referrer,
                            headers=headers
                        )
                        await self.queue_manager.add(task)
                        log.info(f"Download added from browser (no dialog): {url} -> {filename} (priority: {priority})")
                        log.debug(f"Captured headers: {len(headers)} request headers, {len(response_headers)} response headers")
                    except Exception as e:
                        log.error(f"Failed to create download task: {e}")

                await self._send_response(writer, {"status": "received", "url": url})
                return
            else:
                log.warning(f"Unknown message format from extension: {message}")
                await self._send_response(writer, {"error": "unknown_message_type"})
                
        except Exception as e:
            log.error(f"Error handling extension IPC client: {e}")
        finally:
            try:
                writer.close()
                # Don't wait for close to avoid task conflicts with main window
            except Exception as e:
                log.debug(f"Error closing client connection: {e}")


    async def _send_response(self, writer, response: dict):
        """Send a JSON response to the extension."""
        try:
            data = json.dumps(response).encode('utf-8')
            writer.write(data)
            await writer.drain()
        except Exception as e:
            log.error(f"Error sending response to extension: {e}")

    async def _handle_get_qualities(self, url: str) -> dict:
        """Return available stream qualities for a URL."""
        if not url:
            return {"qualities": []}

        cached = self.detected_streams.get(url)
        if cached:
            info = cached.get("info")
            stream_type = cached.get("type")

            if stream_type == "hls" and "variants" in info:
                qualities = []
                for v in info.get("variants", []):
                    qualities.append({
                        "url": v.get("url", url),
                        "resolution": v.get("resolution", "Source"),
                        "bandwidthMbps": v.get("bandwidthMbps"),
                        "label": v.get("label", v.get("resolution", "Source")),
                        "codec": v.get("codec", "Unknown"),
                        "fps": v.get("fps", "N/A"),
                        "type": "HLS",
                        "segmentCount": v.get("segmentCount"),
                        "totalDuration": v.get("totalDuration"),
                    })
                return {"qualities": qualities, "url": url}

            elif stream_type == "dash" and "variants" in info:
                qualities = []
                for v in info.get("variants", []):
                    qualities.append({
                        "url": v.get("url", url),
                        "resolution": v.get("resolution", "unknown"),
                        "bandwidthMbps": v.get("bandwidthMbps"),
                        "label": v.get("label", v.get("resolution", "unknown")),
                        "codec": v.get("codec", "Unknown"),
                        "fps": v.get("fps", "N/A"),
                        "type": v.get("type", "DASH"),
                        "lang": v.get("lang", ""),
                    })
                return {"qualities": qualities, "url": url}

            elif stream_type == "adaptive" and "qualities" in info:
                qualities = []
                for q in info.get("qualities", []):
                    qualities.append({
                        "url": url,
                        "resolution": q.get("resolution"),
                        "label": q.get("label"),
                        "itag": q.get("itag"),
                        "fps": "N/A",
                        "codec": "H.264+AAC",
                        "type": "YouTube",
                    })
                return {"qualities": qualities, "url": url}

        return {
            "qualities": [{
                "url": url,
                "label": "Original",
                "resolution": "Source",
                "type": "Direct Download",
            }],
            "url": url
        }

    def _handle_get_queue_status(self) -> dict:
        """Return current queue and history status."""
        try:
            queue = []
            for task in self.queue_manager.get_all_tasks():
                queue.append({
                    "id": task.id,
                    "url": task.url,
                    "filename": task.filename,
                    "status": task.state.value,
                    "priority": "normal",
                    "attempts": 0,
                    "timestamp": int(task.created_at.timestamp() * 1000) if task.created_at else 0,
                })

            return {
                "queue": queue,
                "history": [],
                "queueLength": len([t for t in self.queue_manager.get_all_tasks() if t.state.value == "queued"]),
                "running": True,
            }
        except Exception as e:
            log.error(f"Error getting queue status: {e}")
            return {"queue": [], "history": [], "queueLength": 0, "running": False}

    def _handle_cancel_item(self, item_id: str) -> dict:
        """Cancel a queued download by ID."""
        try:
            for task in self.queue_manager.get_all_tasks():
                if task.id == item_id:
                    if task.state.value in ("queued", "downloading"):
                        self.queue_manager.cancel(task.id)
                        return {"ok": True}
                    else:
                        return {"ok": False, "error": "task_not_cancellable"}
            return {"ok": False, "error": "not_found"}
        except Exception as e:
            log.error(f"Error canceling item: {e}")
            return {"ok": False, "error": str(e)}

    def _handle_stream_manifest_detected(self, message: dict):
        """Cache stream manifest info from content.js MSE patching."""
        manifest_url = message.get("manifestUrl")
        blob_url = message.get("blobUrl")
        stream_type = message.get("streamType")
        page_url = message.get("pageUrl")

        if manifest_url and stream_type:
            if blob_url:
                self.detected_streams[blob_url] = {
                    "type": stream_type,
                    "manifest_url": manifest_url,
                    "page_url": page_url,
                }
            self.detected_streams[manifest_url] = {
                "type": stream_type,
                "blob_url": blob_url,
                "page_url": page_url,
            }
            log.info(f"Cached stream manifest: {stream_type} - {manifest_url}")


if __name__ == "__main__":
    BrowserExtensionPlugin.run_as_host()
