"""
Spider Manager - Entry Point
"""

import asyncio
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent.resolve()

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from qasync import QEventLoop
from utils.icon_manager import icons
from utils.logger import setup_logging
from utils.sound_manager import get_sound_manager
from resources.icons.icons import Icons

from config import settings as app_settings
from core.download_engine import DownloadEngine
from core.queue_manager import QueueManager
from core.scheduler import downloads_allowed_now
from core.speed_limiter import SpeedLimiter
from ui.download_bridge import DownloadBridge
from ui.main_window import SpiderMainWindow
from plugins.browser_extension import ExtensionIPCHandler


def _scheduler_allows_dispatch() -> bool:
    return downloads_allowed_now(
        enabled=app_settings.get_scheduler_enabled(),
        start_hhmm=app_settings.get_scheduler_start(),
        end_hhmm=app_settings.get_scheduler_end(),
    )


def _cleanup_temp_files():
    """Clean up temporary files on startup if enabled."""
    if app_settings.get_temp_cleanup_enabled():
        try:
            from utils.file_categorizer import DownloadPathManager
            from config.settings import get_download_directory
            
            path_manager = DownloadPathManager(get_download_directory())
            hours = app_settings.get_temp_cleanup_hours()
            cleaned = path_manager.cleanup_temp_files(hours)
            if cleaned > 0:
                print(f"Cleaned up {cleaned} temporary files older than {hours} hours")
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")


def main():
    setup_logging()
    
    _cleanup_temp_files()
    
    # Load default plugins
    from plugins.plugin_base import PluginRegistry
    registry = PluginRegistry.instance()
    registry.load_defaults()
    
    app = QApplication(sys.argv)
    app.setWindowIcon(icons.get_icon(Icons.SPIDER_LOGO))
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    limiter = SpeedLimiter()
    limiter.set_limit_bps(app_settings.get_speed_limit_kb() * 1024)

    engine = DownloadEngine(
        segments=app_settings.get_segment_count(),
        speed_limiter=limiter,
    )
    queue = QueueManager(
        engine,
        max_concurrent=app_settings.get_max_concurrent(),
        scheduler_allows_dispatch=_scheduler_allows_dispatch,
    )
    bridge = DownloadBridge()

    sound_manager = get_sound_manager()
    if app_settings.get_sound_notifications_enabled():
        sound_manager.set_volume(app_settings.get_master_volume())
        
        events = ["download_complete", "download_failed", "queue_finished"]
        for event in events:
            sound_manager.set_event_enabled(event, app_settings.get_sound_enabled(event))
            sound_path = app_settings.get_sound_path(event)
            if sound_path:
                sound_manager.set_sound_path(event, sound_path)

    window = SpiderMainWindow(engine=engine, queue=queue, bridge=bridge)
    
    queue.download_completed.connect(lambda task_id: sound_manager.play(sound_manager.EVENT_DOWNLOAD_COMPLETE))
    queue.download_failed.connect(lambda task_id: sound_manager.play(sound_manager.EVENT_DOWNLOAD_FAILED))
    queue.queue_finished.connect(lambda: sound_manager.play(sound_manager.EVENT_QUEUE_FINISHED))
    window.show()

    ipc_handler = ExtensionIPCHandler(queue, dialog_callback=window._on_intercepted_download)
    loop.call_soon(lambda: asyncio.create_task(ipc_handler.start()))

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
