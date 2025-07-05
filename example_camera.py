import os
import sys
import threading
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class CameraThread(QThread):
    """Thread for handling camera capture"""

    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.paused = False
        self.cap = None
        self.lock = threading.Lock()

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.error_occurred.emit("Failed to open camera")
                return

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            self.running = True

            while self.running:
                if not self.paused:
                    ret, frame = self.cap.read()
                    if ret:
                        self.frame_ready.emit(frame)
                    else:
                        self.error_occurred.emit("Failed to read frame")
                        break
                self.msleep(33)  # ~30 FPS

        except Exception as e:
            self.error_occurred.emit(f"Camera error: {str(e)}")

    def pause(self):
        with self.lock:
            self.paused = True

    def resume(self):
        with self.lock:
            self.paused = False

    def is_paused(self):
        with self.lock:
            return self.paused

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()


class DroneCameraWidget(QWidget):
    """Professional camera widget for drone control app"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_thread = None
        self.is_recording = False
        self.is_paused = False
        self.video_writer = None
        self.current_frame = None
        self.connected = False
        self.recording_frames = []

        self.setupUI()

    def setupUI(self):
        """Setup the user interface"""
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#cameraFrame {
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                color: white;
                min-width: 100px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QPushButton#connectButton {
                background-color: #28a745;
            }
            QPushButton#connectButton:hover {
                background-color: #218838;
            }
            QPushButton#disconnectButton {
                background-color: #dc3545;
            }
            QPushButton#disconnectButton:hover {
                background-color: #c82333;
            }
            QPushButton#recordButton {
                background-color: #dc3545;
            }
            QPushButton#recordButton:hover {
                background-color: #c82333;
            }
            QPushButton#pauseButton {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton#pauseButton:hover {
                background-color: #e0a800;
            }
            QPushButton#resumeButton {
                background-color: #28a745;
            }
            QPushButton#resumeButton:hover {
                background-color: #218838;
            }
            QLabel#titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QLabel#recordingLabel {
                color: #dc3545;
                font-weight: bold;
                font-size: 14px;
            }
        """
        )

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("DRONE CAMERA")
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("background-color: #dc3545; color: white;")
        header_layout.addWidget(self.status_label)

        main_layout.addLayout(header_layout)

        # Camera display
        self.camera_frame = QFrame()
        self.camera_frame.setObjectName("cameraFrame")
        self.camera_frame.setMinimumSize(800, 600)
        self.camera_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        camera_layout = QVBoxLayout()
        camera_layout.setContentsMargins(0, 0, 0, 0)

        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(800, 600)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_label.setStyleSheet("background-color: #0a0a0a; border: none;")

        self.create_professional_placeholder()

        camera_layout.addWidget(self.camera_label)
        self.camera_frame.setLayout(camera_layout)
        main_layout.addWidget(self.camera_frame)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Connection controls
        self.connect_button = QPushButton("CONNECT")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.clicked.connect(self.connect_camera)
        controls_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("DISCONNECT")
        self.disconnect_button.setObjectName("disconnectButton")
        self.disconnect_button.clicked.connect(self.disconnect_camera)
        self.disconnect_button.setEnabled(False)
        controls_layout.addWidget(self.disconnect_button)

        # Spacer
        controls_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Recording controls
        self.record_button = QPushButton("RECORD")
        self.record_button.setObjectName("recordButton")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        controls_layout.addWidget(self.record_button)

        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        controls_layout.addWidget(self.pause_button)

        # Recording status
        self.recording_label = QLabel("")
        self.recording_label.setObjectName("recordingLabel")
        controls_layout.addWidget(self.recording_label)

        main_layout.addLayout(controls_layout)
        self.setLayout(main_layout)

        # Timer for recording indicator blink
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_recording_indicator)
        self.blink_state = False

    def create_professional_placeholder(self):
        """Create a professional-looking placeholder"""
        pixmap = QPixmap(800, 600)
        pixmap.fill(QColor(10, 10, 10))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw grid pattern
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        for x in range(0, 800, 50):
            painter.drawLine(x, 0, x, 600)
        for y in range(0, 600, 50):
            painter.drawLine(0, y, 800, y)

        # Draw center crosshair
        center_x, center_y = 400, 300
        painter.setPen(QPen(QColor(0, 120, 212), 3))
        painter.drawLine(center_x - 50, center_y, center_x + 50, center_y)
        painter.drawLine(center_x, center_y - 50, center_x, center_y + 50)
        painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)

        # Draw camera icon
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(30, 30, 30)))

        # Camera body
        camera_rect = [center_x - 80, center_y - 120, 160, 80]
        painter.drawRoundedRect(*camera_rect, 10, 10)

        # Lens
        painter.setPen(QPen(QColor(150, 150, 150), 3))
        painter.setBrush(QBrush(QColor(20, 20, 20)))
        painter.drawEllipse(center_x - 35, center_y - 110, 70, 70)

        # Lens inner circle
        painter.setPen(QPen(QColor(0, 120, 212), 2))
        painter.drawEllipse(center_x - 25, center_y - 100, 50, 50)

        # Text
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
        painter.drawText(
            center_x - 100, center_y + 60, 200, 30, Qt.AlignCenter, "CAMERA OFFLINE"
        )

        painter.setFont(QFont("Segoe UI", 12))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawText(
            center_x - 120,
            center_y + 90,
            240,
            20,
            Qt.AlignCenter,
            "Click CONNECT to start video stream",
        )

        # Status indicators
        painter.setPen(QPen(QColor(220, 53, 69), 2))
        painter.setBrush(QBrush(QColor(220, 53, 69)))
        painter.drawEllipse(50, 50, 15, 15)

        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(75, 63, "NO SIGNAL")

        painter.end()
        self.camera_label.setPixmap(pixmap)

    def connect_camera(self):
        """Connect to camera"""
        try:
            self.camera_thread = CameraThread(0)
            self.camera_thread.frame_ready.connect(self.update_frame)
            self.camera_thread.error_occurred.connect(self.handle_camera_error)
            self.camera_thread.start()

            self.connected = True
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.record_button.setEnabled(True)
            self.pause_button.setEnabled(True)

            self.status_label.setText("CONNECTED")
            self.status_label.setStyleSheet("background-color: #28a745; color: white;")

        except Exception as e:
            self.handle_camera_error(f"Connection failed: {str(e)}")

    def disconnect_camera(self):
        """Disconnect from camera"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None

        if self.is_recording:
            self.stop_recording()

        self.connected = False
        self.is_paused = False

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.pause_button.setEnabled(False)

        self.status_label.setText("DISCONNECTED")
        self.status_label.setStyleSheet("background-color: #dc3545; color: white;")

        self.create_professional_placeholder()

    def handle_camera_error(self, error_message):
        """Handle camera errors"""
        self.status_label.setText(f"ERROR: {error_message}")
        self.status_label.setStyleSheet("background-color: #dc3545; color: white;")

    def update_frame(self, frame):
        """Update camera frame display"""
        self.current_frame = frame.copy()

        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to fit
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Add overlays
        painter = QPainter(scaled_pixmap)

        # Recording indicator
        if self.is_recording and self.blink_state:
            painter.setPen(QPen(Qt.red, 3))
            painter.setBrush(QBrush(Qt.red))
            painter.drawEllipse(scaled_pixmap.width() - 40, 20, 20, 20)

            painter.setPen(QPen(Qt.white, 2))
            painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
            painter.drawText(scaled_pixmap.width() - 80, 45, "REC")

        # Pause indicator
        if self.is_paused:
            painter.setPen(QPen(Qt.yellow, 3))
            painter.setBrush(QBrush(Qt.yellow))
            painter.drawRect(scaled_pixmap.width() - 40, 60, 8, 20)
            painter.drawRect(scaled_pixmap.width() - 28, 60, 8, 20)

            painter.setPen(QPen(Qt.white, 2))
            painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
            painter.drawText(scaled_pixmap.width() - 90, 95, "PAUSED")

        painter.end()
        self.camera_label.setPixmap(scaled_pixmap)

        # Record frame if recording and not paused
        if self.is_recording and not self.is_paused and self.video_writer:
            self.video_writer.write(frame)

    def toggle_recording(self):
        """Toggle recording"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start recording"""
        if not self.connected or self.current_frame is None:
            return

        try:
            os.makedirs("recordings", exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recordings/drone_feed_{timestamp}.mp4"

            h, w = self.current_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(filename, fourcc, 30.0, (w, h))

            self.is_recording = True
            self.record_button.setText("STOP")
            self.recording_label.setText("● RECORDING")
            self.blink_timer.start(500)  # Blink every 500ms

        except Exception as e:
            self.handle_camera_error(f"Recording failed: {str(e)}")

    def stop_recording(self):
        """Stop recording"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.is_recording = False
        self.record_button.setText("RECORD")
        self.recording_label.setText("")
        self.blink_timer.stop()

    def toggle_pause(self):
        """Toggle pause"""
        if not self.connected or not self.camera_thread:
            return

        if not self.is_paused:
            self.camera_thread.pause()
            self.is_paused = True
            self.pause_button.setText("RESUME")
            self.pause_button.setObjectName("resumeButton")
            self.pause_button.setStyleSheet(self.styleSheet())  # Refresh style
        else:
            self.camera_thread.resume()
            self.is_paused = False
            self.pause_button.setText("PAUSE")
            self.pause_button.setObjectName("pauseButton")
            self.pause_button.setStyleSheet(self.styleSheet())  # Refresh style

    def blink_recording_indicator(self):
        """Blink recording indicator"""
        self.blink_state = not self.blink_state

    def closeEvent(self, event):
        """Cleanup on close"""
        self.disconnect_camera()
        event.accept()


# Test application
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("MATEK Drone Control Center - Camera")
    window.setGeometry(100, 100, 1000, 800)
    window.setStyleSheet("background-color: #2b2b2b;")

    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)

    camera_widget = DroneCameraWidget()
    layout.addWidget(camera_widget)

    window.setLayout(layout)
    window.show()

    sys.exit(app.exec())
