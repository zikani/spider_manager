"""
speed_graph.py - Real-time speed chart (QWidget with custom paint).
"""

from collections import deque

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPolygonF
from PyQt6.QtWidgets import QWidget


class SpeedGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(90)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("#161b22"))
        self.setPalette(pal)

        self.data = deque(maxlen=60)
        for _ in range(60):
            self.data.append(0.0)
        self.peak = 0.0

    def add_sample_mbps(self, speed_bps: float) -> None:
        mbps = speed_bps / (1024 * 1024) if speed_bps > 0 else 0.0
        self.data.append(mbps)
        if mbps > self.peak:
            self.peak = mbps
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height() - 20

        painter.setPen(QColor("#8b949e"))
        painter.drawText(6, 14, "↓ Download Speed (last 60s)")
        peak_text = f"Peak: {self.peak:.1f} MB/s"
        painter.drawText(w - painter.fontMetrics().horizontalAdvance(peak_text) - 6, 14, peak_text)

        graph_left = 6
        graph_top = 22
        graph_width = w - 12
        graph_height = h - 26

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0d1117"))
        painter.drawRoundedRect(graph_left, graph_top, graph_width, graph_height, 4, 4)

        pen = QPen(QColor("#21262d"), 0.5)
        painter.setPen(pen)
        for frac in [0.25, 0.5, 0.75]:
            y = graph_top + graph_height * (1 - frac)
            painter.drawLine(graph_left, int(y), graph_left + graph_width, int(y))

        max_val = max(max(self.data), 0.01) if self.data else 0.01
        points = []
        n = len(self.data)
        for i, val in enumerate(self.data):
            x = graph_left + (i / max(n - 1, 1)) * graph_width
            y = graph_top + graph_height * (1 - val / max_val)
            points.append(QPointF(x, y))

        gradient = QLinearGradient(0, graph_top, 0, graph_top + graph_height)
        gradient.setColorAt(0, QColor(88, 166, 255, 64))
        gradient.setColorAt(1, QColor(88, 166, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))

        poly = [QPointF(graph_left, graph_top + graph_height)]
        poly.extend(points)
        poly.append(QPointF(graph_left + graph_width, graph_top + graph_height))
        painter.drawPolygon(QPolygonF(poly))

        pen = QPen(QColor("#58a6ff"), 1.5)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        painter.end()
