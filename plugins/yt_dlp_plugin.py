"""
yt_dlp_plugin.py - Video extraction plugin using yt-dlp.
"""

import asyncio
from plugins.plugin_base import SpiderPlugin

class YtDlpPlugin(SpiderPlugin):
    @property
    def name(self) -> str:
        return "yt-dlp"

    @property
    def description(self) -> str:
        return "Extracts video/audio from 1000+ sites using yt-dlp."

    def can_handle(self, url: str) -> bool:
        # Simplified check for video sites
        video_sites = ["youtube.com", "youtu.be", "vimeo.com", "twitch.tv", "facebook.com", "twitter.com", "instagram.com"]
        return any(site in url.lower() for site in video_sites)

    async def process(self, url: str) -> dict:
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("yt-dlp package is not installed.")

        def _extract():
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "url": info["url"],
                    "filename": f"{info['title']}.{info['ext']}",
                    "size": info.get("filesize") or info.get("filesize_approx") or 0,
                    "headers": info.get("http_headers", {})
                }

        # Run yt-dlp in a thread to keep UI responsive
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)
