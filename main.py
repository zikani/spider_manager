"""
Spider Manager - Entry Point
"""

import asyncio
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from qasync import QEventLoop
from utils.icon_manager import icons
from utils.logger import setup_logging
from resources.icons.icons import Icons

from config import settings as app_settings
from core.download_engine import DownloadEngine
from core.queue_manager import QueueManager
from core.scheduler import downloads_allowed_now
from core.speed_limiter import SpeedLimiter
from ui.download_bridge import DownloadBridge
from ui.main_window import SpiderMainWindow


def _scheduler_allows_dispatch() -> bool:
    return downloads_allowed_now(
        enabled=app_settings.get_scheduler_enabled(),
        start_hhmm=app_settings.get_scheduler_start(),
        end_hhmm=app_settings.get_scheduler_end(),
    )


def main():
    setup_logging()
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

    window = SpiderMainWindow(engine=engine, queue=queue, bridge=bridge)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
