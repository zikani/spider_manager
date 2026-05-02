"""
category_panel.py - Left sidebar category tree with filters.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from utils.icon_manager import icons
from resources.icons.icons import Icons

from config.constants import DownloadState
from core.queue_manager import QueueManager


class CategoryItem(QFrame):
    def __init__(self, icon, text, count=0, active=False, filter_id=""):
        super().__init__()
        self.setFixedHeight(28)
        self.active = active
        self.icon = icon
        self.text = text
        self.count = count
        self.filter_id = filter_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_count(self, n: int) -> None:
        self.count = n
        self.update()

    def update_style(self):
        if self.active:
            self.setStyleSheet(
                "background: rgba(31,111,235,0.18); border-radius: 6px; color: #58a6ff;"
            )
        else:
            self.setStyleSheet("background: transparent; border-radius: 6px;")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background if hovered or active
        if self.active:
            painter.setBrush(QColor("rgba(31,111,235,0.18)"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(self.rect()), 6, 6)

        # Draw Icon
        if self.icon:
            icon_rect = QRectF(12, 6, 16, 16)
            self.icon.paint(painter, icon_rect.toRect())

        # Draw Text
        font = QFont("Segoe UI", 10, QFont.Weight.Medium if self.active else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#58a6ff") if self.active else QColor("#e6edf3"))
        painter.drawText(38, 19, self.text)

        # Draw Badge
        badge_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(badge_font)
        badge_bg = QColor("rgba(88,166,255,0.2)" if self.active else "#21262d")
        painter.setBrush(badge_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        
        badge_text = str(self.count)
        badge_width = painter.fontMetrics().horizontalAdvance(badge_text) + 12
        badge_rect = QRectF(self.width() - badge_width - 8, 6, badge_width, 16)
        
        painter.drawRoundedRect(badge_rect, 8, 8)
        painter.setPen(QColor("#58a6ff") if self.active else QColor("#8b949e"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
        painter.end()


class CategoryPanel(QWidget):
    filter_changed = pyqtSignal(str)

    def __init__(self, queue: QueueManager):
        super().__init__()
        self._queue = queue
        self.setFixedWidth(190)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("#161b22"))
        self.setPalette(pal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        def add_section(text):
            label = QLabel(text)
            label.setStyleSheet(
                "color: #8b949e; font-size: 10px; font-weight: bold; padding: 10px 16px 4px;"
            )
            layout.addWidget(label)

        add_section("CATEGORIES")
        self.all_dl = CategoryItem(icons.get_icon(Icons.VIEW_LIST), "All Downloads", 0, active=True, filter_id="all")
        self._wire_item(self.all_dl)
        layout.addWidget(self.all_dl)

        self.item_downloading = CategoryItem(icons.get_icon(Icons.PLAY), "Downloading", 0, filter_id="downloading")
        self.item_paused = CategoryItem(icons.get_icon(Icons.PAUSE), "Paused", 0, filter_id="paused")
        self.item_completed = CategoryItem(icons.get_icon(Icons.STATUS_COMPLETE), "Completed", 0, filter_id="completed")
        self.item_failed = CategoryItem(icons.get_icon(Icons.STATUS_ERROR), "Failed", 0, filter_id="failed")
        self.category_items = [
            self.all_dl,
            self.item_downloading,
            self.item_paused,
            self.item_completed,
            self.item_failed,
        ]
        for it in self.category_items[1:]:
            self._wire_item(it)
            layout.addWidget(it)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFrameShadow(QFrame.Shadow.Plain)
        div.setStyleSheet(
            "background-color: #30363d; margin: 6px 12px; height: 1px; border: none;"
        )
        layout.addWidget(div)

        add_section("FILE TYPE")
        type_specs = [
            (icons.get_icon(Icons.FILE_VIDEO), "Video", "Video"),
            (icons.get_icon(Icons.FILE_AUDIO), "Audio", "Audio"),
            (icons.get_icon(Icons.FILE), "Documents", "Document"),
            (icons.get_icon(Icons.FILE_ARCHIVE), "Archives", "Archive"),
            (icons.get_icon(Icons.SETTINGS), "Programs", "Program"),
        ]
        self.type_items: list[CategoryItem] = []
        for icon, label, cat in type_specs:
            it = CategoryItem(icon, label, 0, filter_id=f"cat:{cat}")
            self._wire_item(it)
            self.type_items.append(it)
            layout.addWidget(it)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setFrameShadow(QFrame.Shadow.Plain)
        div2.setStyleSheet(
            "background-color: #30363d; margin: 6px 12px; height: 1px; border: none;"
        )
        layout.addWidget(div2)

        add_section("SCHEDULER")
        self.sched = CategoryItem(icons.get_icon(Icons.SCHEDULER), "Scheduled", 0, filter_id="all")
        self._wire_item(self.sched)
        layout.addWidget(self.sched)

        self.speed_box = QWidget()
        self.speed_box.setObjectName("speedBox")
        self.speed_box.setStyleSheet(
            """
            #speedBox { background: #21262d; border-radius: 8px; margin: 12px; }
            QLabel { background: transparent; }
        """
        )
        speed_layout = QVBoxLayout(self.speed_box)
        speed_layout.setContentsMargins(12, 10, 12, 10)
        speed_layout.setSpacing(2)

        speed_label = QLabel("TOTAL SPEED")
        speed_label.setStyleSheet(
            "color: #8b949e; font-size: 10px; font-weight: 600; "
            "text-transform: uppercase; letter-spacing: 0.5px;"
        )
        self.speed_value = QLabel("0")
        self.speed_value.setStyleSheet(
            "color: #58a6ff; font-size: 20px; font-weight: 700;"
        )
        unit = QLabel("MB/s download")
        unit.setStyleSheet("color: #8b949e; font-size: 11px;")

        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_value)
        speed_layout.addWidget(unit)
        layout.addWidget(self.speed_box)

        layout.addStretch()

    def _wire_item(self, item: CategoryItem):
        def handler(_e, it=item):
            self._set_active(it)
            self.filter_changed.emit(it.filter_id)

        item.mousePressEvent = handler

    def _set_active(self, item: CategoryItem):
        for it in self.category_items + self.type_items + [self.sched]:
            it.active = it is item
            it.update_style()
        self.update()

    def update_counts(self) -> None:
        tasks = self._queue.tasks_snapshot()
        n_all = len(tasks)
        n_dl = sum(
            1
            for t in tasks
            if t.state in (DownloadState.DOWNLOADING, DownloadState.MERGING)
        )
        n_ps = sum(1 for t in tasks if t.state == DownloadState.PAUSED)
        n_ok = sum(1 for t in tasks if t.state == DownloadState.COMPLETED)
        n_fail = sum(
            1 for t in tasks if t.state in (DownloadState.ERROR, DownloadState.CANCELLED)
        )

        self.all_dl.set_count(n_all)
        self.item_downloading.set_count(n_dl)
        self.item_paused.set_count(n_ps)
        self.item_completed.set_count(n_ok)
        self.item_failed.set_count(n_fail)

        by_cat: dict[str, int] = {}
        for t in tasks:
            by_cat[t.category] = by_cat.get(t.category, 0) + 1
        for it in self.type_items:
            key = it.filter_id[4:] if it.filter_id.startswith("cat:") else ""
            it.set_count(by_cat.get(key, 0))

        self.sched.set_count(0)

    def set_total_speed_mbps(self, mbps: float) -> None:
        self.speed_value.setText(f"{mbps:.2f}")
