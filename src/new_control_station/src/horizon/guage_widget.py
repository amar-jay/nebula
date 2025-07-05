from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ModernGauge(QWidget):
    """Base class for modern circular gauges"""

    def __init__(self, title="", unit="", min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.value = 0
        self.target_value = 0
        self.setMinimumSize(140, 140)

        # Modern colors
        self.bg_color = QColor(20, 25, 31)
        self.ring_color = QColor(45, 52, 63)
        self.accent_color = QColor(0, 150, 255)
        self.text_color = QColor(255, 255, 255)
        self.warning_color = QColor(255, 165, 0)
        self.danger_color = QColor(255, 69, 58)

    def set_value(self, value):
        self.target_value = max(self.min_val, min(self.max_val, value))
        self.value = self.target_value  # For smooth animation, you could interpolate
        self.update()

    def get_color_for_value(self, value):
        # Override in subclasses for custom color logic
        return self.accent_color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 20

        # Background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.bg_color))
        painter.drawEllipse(center, radius, radius)

        # Ring background
        painter.setPen(QPen(self.ring_color, 8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - 15, radius - 15)

        # Value arc
        start_angle = 225  # Start from bottom left
        span_angle = 270  # 3/4 circle

        if self.max_val != self.min_val:
            value_angle = (
                (self.value - self.min_val) / (self.max_val - self.min_val) * span_angle
            )
            painter.setPen(
                QPen(
                    self.get_color_for_value(self.value),
                    8,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawArc(
                center.x() - radius + 15,
                center.y() - radius + 15,
                (radius - 15) * 2,
                (radius - 15) * 2,
                start_angle * 16,
                -value_angle * 16,
            )

        # Center circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.ring_color))
        painter.drawEllipse(center, radius - 35, radius - 35)

        # Value text
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        value_text = f"{self.value:.1f}"
        text_rect = painter.fontMetrics().boundingRect(value_text)
        painter.drawText(
            center.x() - text_rect.width() // 2, center.y() + 5, value_text
        )

        # Unit text
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(self.text_color.darker(150)))
        unit_rect = painter.fontMetrics().boundingRect(self.unit)
        painter.drawText(
            center.x() - unit_rect.width() // 2, center.y() + 20, self.unit
        )

        # Title
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.setPen(QPen(self.text_color))
        title_rect = painter.fontMetrics().boundingRect(self.title)
        painter.drawText(center.x() - title_rect.width() // 2, 25, self.title)


class AltitudeGauge(ModernGauge):
    """Altitude gauge"""

    def __init__(self, parent=None):
        super().__init__("ALTITUDE", "m", 0, 30, parent)


class SpeedGauge(ModernGauge):
    """Speed gauge"""

    def __init__(self, parent=None):
        super().__init__("SPEED", "m/s", 0, 30, parent)


class BatteryGauge(ModernGauge):
    """Battery level gauge with color coding"""

    def __init__(self, parent=None):
        super().__init__("BATTERY", "%", 0, 100, parent)

    def get_color_for_value(self, value):
        if value > 50:
            return QColor(52, 199, 89)  # Green
        elif value > 20:
            return QColor(255, 159, 10)  # Orange
        else:
            return QColor(255, 69, 58)  # Red
