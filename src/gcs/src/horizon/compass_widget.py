import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class CompassWidget(QWidget):
    """Modern compass widget"""

    def __init__(self, title="COMPASS", parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 140)
        self.heading = 0.0
        self.title = title

    def set_heading(self, heading):
        self.heading = heading % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 20

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 25, 31)))
        painter.drawEllipse(center, radius, radius)

        # Compass ring
        painter.setPen(QPen(QColor(45, 52, 63), 8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - 15, radius - 15)

        # Cardinal directions
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        directions = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        for direction, angle in directions:
            rad = math.radians(angle - 90)
            x = center.x() + (radius - 30) * math.cos(rad)
            y = center.y() + (radius - 30) * math.sin(rad)

            text_rect = painter.fontMetrics().boundingRect(direction)
            painter.drawText(
                x - text_rect.width() // 2, y + text_rect.height() // 2, direction
            )

        # Heading needle
        painter.setPen(QPen(QColor(255, 69, 58), 4))
        needle_rad = math.radians(self.heading - 90)
        needle_x = center.x() + (radius - 25) * math.cos(needle_rad)
        needle_y = center.y() + (radius - 25) * math.sin(needle_rad)
        painter.drawLine(center, QPointF(needle_x, needle_y))

        # Center dot
        painter.setBrush(QBrush(QColor(255, 69, 58)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 4, 4)

        # Heading text
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        heading_text = f"{int(self.heading)}°"
        text_rect = painter.fontMetrics().boundingRect(heading_text)
        painter.drawText(
            center.x() - text_rect.width() // 2, center.y() + 25, heading_text
        )

        # Title
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255)))
        title_rect = painter.fontMetrics().boundingRect(self.title)
        painter.drawText(center.x() - title_rect.width() // 2, 25, self.title)
