"""
Sound Manager - Handle sound notifications for download events.
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl, QObject

from utils.logger import get_logger

log = get_logger(__name__)


class SoundManager(QObject):
    """
    Manages sound notifications for various download events.
    Uses QSoundEffect for playing sound files.
    """
    
    EVENT_DOWNLOAD_COMPLETE = "download_complete"
    EVENT_DOWNLOAD_FAILED = "download_failed"
    EVENT_QUEUE_FINISHED = "queue_finished"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._effects: dict[str, QSoundEffect] = {}
        self._sound_paths: dict[str, str] = {}
        self._enabled: dict[str, bool] = {
            self.EVENT_DOWNLOAD_COMPLETE: True,
            self.EVENT_DOWNLOAD_FAILED: True,
            self.EVENT_QUEUE_FINISHED: True,
        }
        self._volume: float = 0.7
        
    def set_sound_path(self, event: str, path: str) -> None:
        """Set the sound file path for a specific event."""
        if not path or not Path(path).exists():
            log.warning("Invalid sound path for %s: %s", event, path)
            return
        
        self._sound_paths[event] = path
        if event in self._effects:
            self._effects[event].deleteLater()
            del self._effects[event]
        
        log.debug("Sound path set for %s: %s", event, path)
    
    def get_sound_path(self, event: str) -> Optional[str]:
        """Get the current sound file path for an event."""
        return self._sound_paths.get(event)
    
    def set_event_enabled(self, event: str, enabled: bool) -> None:
        """Enable or disable sound for a specific event."""
        self._enabled[event] = enabled
        log.debug("Sound %s for event %s", "enabled" if enabled else "disabled", event)
    
    def is_event_enabled(self, event: str) -> bool:
        """Check if sound is enabled for a specific event."""
        return self._enabled.get(event, False)
    
    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        log.debug("Volume set to %.2f", self._volume)
    
    def get_volume(self) -> float:
        """Get current master volume."""
        return self._volume
    
    def play(self, event: str) -> None:
        """
        Play sound for a specific event.
        Silently fails if sound is disabled or file not found.
        """
        if not self._enabled.get(event, False):
            log.debug("Sound disabled for event: %s", event)
            return
        
        sound_path = self._sound_paths.get(event)
        if not sound_path or not Path(sound_path).exists():
            log.warning("Cannot play sound for %s: no valid file", event)
            return
        
        try:
            if event not in self._effects or self._effects[event].status() == QSoundEffect.Status.Null:
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(sound_path))
                effect.setVolume(self._volume)
                self._effects[event] = effect
            
            effect = self._effects[event]
            
            if effect.status() == QSoundEffect.Status.Ready:
                effect.play()
                log.debug("Playing sound for event: %s", event)
            else:
                log.warning("Sound effect not ready for %s (status: %s)", 
                          event, effect.status())
                
        except Exception as e:
            log.error("Error playing sound for %s: %s", event, e)
    
    def play_preview(self, sound_path: str) -> None:
        """
        Play a sound file for preview purposes.
        Used in the preferences dialog.
        """
        if not sound_path or not Path(sound_path).exists():
            log.warning("Cannot preview sound: invalid path")
            return
        
        try:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(sound_path))
            effect.setVolume(self._volume)
            
            if effect.status() == QSoundEffect.Status.Ready:
                effect.play()
                log.debug("Previewing sound: %s", sound_path)
            else:
                log.warning("Sound effect not ready for preview (status: %s)", effect.status())
                
        except Exception as e:
            log.error("Error previewing sound: %s", e)
    
    def stop_all(self) -> None:
        """Stop all currently playing sounds."""
        for effect in self._effects.values():
            if effect.isPlaying():
                effect.stop()
        log.debug("All sounds stopped")


_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get the global sound manager instance."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
