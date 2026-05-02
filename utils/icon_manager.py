import os
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

class IconManager:
    _instance = None
    _icon_cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            # Base path for icons - assuming we are in utils/ and resources is at root
            cls._instance.base_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "resources", "icons"
            ))
        return cls._instance

    def get_icon(self, icon_path: str) -> QIcon:
        """Loads an icon from the resources/icons directory."""
        if icon_path in self._icon_cache:
            return self._icon_cache[icon_path]
        
        full_path = os.path.join(self.base_path, icon_path)
        if not os.path.exists(full_path):
            # Fallback to a generic icon if missing
            return QIcon()
            
        icon = QIcon(full_path)
        self._icon_cache[icon_path] = icon
        return icon

# Global instance
icons = IconManager()
