"""
plugin_base.py - Base class for Spider Manager plugins.
"""

from abc import ABC, abstractmethod

class SpiderPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this plugin can handle the given URL."""
        pass

    @abstractmethod
    async def process(self, url: str) -> dict:
        """
        Process the URL and return metadata for download.
        Expected return dict:
        {
            "url": str,
            "filename": str,
            "size": int,
            "headers": dict (optional)
        }
        """
        pass
