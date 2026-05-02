"""
progress_delegate.py - Custom progress bar cell renderer.
"""
from PyQt6.QtCore import Qt, QRect, QPointF, QSize
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QIcon
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from utils.icon_manager import icons
from resources.icons.icons import Icons

# Map UI states to SVG icons
STATE_SVG = {
    "dl": Icons.PLAY,
    "ok": Icons.STATUS_COMPLETE,
    "ps": Icons.PAUSE,
    "er": Icons.STATUS_ERROR,
    "q": Icons.STATUS_QUEUED,
    "ca": Icons.STOP,
}


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        # Get progress value
        progress = index.data(Qt.ItemDataRole.DisplayRole)
        if progress is None or not isinstance(progress, (int, float)):
            progress = 0
        state_row = index.siblingAtColumn(0).data(Qt.ItemDataRole.DisplayRole) or "?"
        # Map state to row icon to infer state
        state = "dl"
        if state_row in ["✓"]:
            state = "ok"
        elif state_row in ["⏸"]:
            state = "ps"
        elif state_row in ["!"]:
            state = "er"
        elif state_row in ["…"]:
            state = "q"
        elif state_row in ["✕"]:
            state = "ca"

        # Draw background
        bg_rect = option.rect.adjusted(2, 5, -2, -5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#21262d"))
        painter.drawRoundedRect(bg_rect, 5, 5)

        if state == "er":
            fill_color = QColor("#f78166")
        elif state == "ca":
            fill_color = QColor("#484f58")
        elif state == "ok":
            gradient = QLinearGradient(QPointF(bg_rect.topLeft()), QPointF(bg_rect.topRight()))
            gradient.setColorAt(0, QColor("#238636"))
            gradient.setColorAt(1, QColor("#3fb950"))
            fill_color = QBrush(gradient)
        else:
            gradient = QLinearGradient(QPointF(bg_rect.topLeft()), QPointF(bg_rect.topRight()))
            gradient.setColorAt(0, QColor("#1f6feb"))
            gradient.setColorAt(1, QColor("#58a6ff"))
            fill_color = QBrush(gradient)

        # Draw fill
        fill_width = bg_rect.width() * progress / 100
        if fill_width > 0:
            fill_rect = QRect(bg_rect)
            fill_rect.setWidth(int(fill_width))
            painter.setBrush(fill_color)
            painter.drawRoundedRect(fill_rect, 5, 5)

        # Draw State Icon
        icon_enum = STATE_SVG.get(state)
        if icon_enum:
            icon = icons.get_icon(icon_enum)
            icon_size = 12
            icon_x = bg_rect.left() + 6
            icon_y = bg_rect.top() + (bg_rect.height() - icon_size) // 2
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            icon.paint(painter, icon_rect)

        # Text
        if state == "er":
            text = "Error"
        elif state == "ca":
            text = "—"
        else:
            text = f"{int(progress)}%"
        
        painter.setPen(
            QColor("#f78166")
            if state == "er"
            else QColor("#ffffff") if progress > 50 else QColor("#8b949e")
        )
        # Offset text to not overlap icon
        text_rect = option.rect.adjusted(20, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()
        return