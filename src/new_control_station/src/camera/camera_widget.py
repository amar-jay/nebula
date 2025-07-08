import sys

import cv2
from typing import Optional
import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton as _PrimaryPushButton
from qfluentwidgets import PushButton as QPushButton
from src.mq.zmq_client import ZMQClient


def ConnectButton(text):
    btn = _PrimaryPushButton(text)
    return btn


class CameraWidget(QWidget):
    """Custom camera widget matching the drone control app style"""

    def __init__(self, parent=None, video_client:Optional[ZMQClient]=None):
        super().__init__(parent)
        self.current_frame = None
        self.is_connected = False
        self.is_recording = False
        self.video_writer = None
        self.recording_filename = None
        self.video_client = video_client

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Setup the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Camera display frame
        self.camera_frame = QFrame()
        self.camera_frame.setFrameStyle(QFrame.Shape.Box)
        self.camera_frame.setLineWidth(1)
        self.camera_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Camera display label
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Camera frame layout
        camera_layout = QVBoxLayout(self.camera_frame)
        camera_layout.setContentsMargins(5, 5, 5, 5)
        camera_layout.addWidget(self.camera_label)

        # Control panel
        control_panel = QFrame()
        control_panel.setFixedHeight(60)
        control_panel.setFrameStyle(QFrame.Shape.Box)
        control_panel.setLineWidth(1)

        # Control buttons layout
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(10)

        # Connect button
        self.connect_btn = ConnectButton("Connect")
        self.connect_btn.setFixedSize(100, 35)
        self.connect_btn.clicked.connect(self.toggle_connection)

        # Record button
        self.record_btn = QPushButton("🔴")
        self.record_btn.setToolTip("Start/Stop Recording")
        self.record_btn.setFixedSize(50, 35)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(False)

        # Pause button
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setToolTip("Pause/Resume Recording")
        self.pause_btn.setFixedSize(50, 35)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)

        # Status label
        self.status_label = QLabel("Camera Disconnected")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Recording indicator
        self.recording_indicator = QLabel("●")
        self.recording_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recording_indicator.setFixedSize(30, 30)
        self.recording_indicator.hide()

        # Add controls to layout
        control_layout.addWidget(self.connect_btn)
        control_layout.addWidget(self.record_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.recording_indicator)

        # Add to main layout
        main_layout.addWidget(self.camera_frame)
        main_layout.addWidget(control_panel)

        # Show placeholder
        self.show_placeholder()

    def setup_style(self):
        """Apply the dark theme styling to match the app"""
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            
            QFrame {
                background-color: #363636;
                border: 1px solid #555555;
                border-radius: 5px;
            }
            
            QLabel {
                background-color: transparent;
                border: none;
                color: #ffffff;
            }
        """
        )

        # Set object names for specific styling
        self.connect_btn.setObjectName("connectBtn")
        self.record_btn.setObjectName("recordBtn")

    def show_placeholder(self):
        """Show placeholder when camera is not connected"""
        placeholder = QPixmap(
			"src/new_control_station/assets/images/logo.png_"
        )  # Path to your image asset

        if placeholder.isNull():
            placeholder = QPixmap(640, 480)
            self.show_placeholder_fallback(placeholder)
            # placeholder.fill(QColor(54, 54, 54))

        scaled_placeholder = placeholder.scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(scaled_placeholder)

    def show_placeholder_fallback(self, placeholder):
        """Show placeholder when camera is not connected"""
        # Create a placeholder image
        placeholder.fill(QColor(54, 54, 54))

        # Draw placeholder content
        painter = QPainter(placeholder)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw camera icon (simple representation)
        pen = QPen(QColor(150, 150, 150), 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(80, 80, 80)))

        # Camera body
        painter.drawRoundedRect(270, 210, 100, 60, 10, 10)
        # Camera lens
        painter.drawEllipse(310, 230, 20, 20)
        # Camera text
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(260, 300, "Disconnected")

        painter.end()

        self.camera_label.setPixmap(placeholder)

    def toggle_connection(self):
        """Toggle camera connection"""
        if not self.is_connected:
            self.connect_camera()
        else:
            self.disconnect_camera()

    def connect_camera(self):
        """Connect to camera"""
        try:
            self.video_client.video_thread.frame_received.connect(self.update_frame)

            self.video_client.start()

            self.is_connected = True
            self.connect_btn.setText("Disconnect")
            self.record_btn.setEnabled(True)
            self.status_label.setText("Camera Connected")

        except Exception as e:
            print(f"Error connecting to camera: {e}")
            self.status_label.setText("Connection Failed")

    def disconnect_camera(self):
        """Disconnect from camera"""
        self.video_client.video_thread.stop()
        if self.is_recording:
            self.stop_recording()

        self.is_connected = False
        self.connect_btn.setText("Connect")
        self.record_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("Camera Disconnected")

        self.show_placeholder()

    @Slot(np.ndarray)
    def update_frame(self, frame):
        """Update camera frame display"""
        if self.is_connected and (frame is not None):
            self.current_frame = frame.copy()

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w

            # Create QImage and scale to fit
            qt_image = QImage(
                rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qt_image)

            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            self.camera_label.setPixmap(scaled_pixmap)

            # Write frame if recording or not paused
            if (
                self.is_recording
                and self.video_writer
                and self.pause_btn.text() == "⏸️"
            ):
                self.video_writer.write(frame)

    def toggle_recording(self):
        """Toggle video recording"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start video recording"""
        if not self.is_connected:
            return

        try:
            import os
            import time

            # Create directory if it doesn't exist
            os.makedirs("recordings", exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.recording_filename = os.path.join(
                "recordings", f"drone_recording_{timestamp}.mp4"
            )

            # Setup video writer
            frame_size = (self.current_frame.shape[1], self.current_frame.shape[0])  # (width, height)

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(
                self.recording_filename, fourcc, 10.0, frame_size
            )

            self.is_recording = True
            self.record_btn.setText("🟥")
            self.pause_btn.setEnabled(True)
            self.recording_indicator.show()
            self.recording_indicator.setStyleSheet("color: #d83b01; font-size: 20px;")
            self.status_label.setText(f"Recording: {self.recording_filename}")

        except Exception as e:
            print(f"Error starting recording: {e}")
            self.status_label.setText("Recording Failed")

    def stop_recording(self):
        """Stop video recording"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.is_recording = False
        self.record_btn.setText("🔴")
        self.pause_btn.setEnabled(False)
        self.recording_indicator.hide()
        self.status_label.setText(
            "Recording Saved" if self.recording_filename else "Camera Connected"
        )

    def toggle_pause(self):
        """Toggle recording pause (simple implementation)"""
        if self.pause_btn.text() == "⏸️":
            self.pause_btn.setText("▶️")
            # In a full implementation, you'd pause the video writer
            self.status_label.setText("Recording Paused")
        else:
            self.pause_btn.setText("⏸️")
            self.status_label.setText("Recording Resumed")

    def closeEvent(self, event):
        """Clean up when widget is closed"""
        if self.video_client:
            self.video_client.stop()
        if self.video_writer:
            self.video_writer.release()
        event.accept()

# Example usage and testing
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create main window to test the widget
    window = QWidget()
    window.setWindowTitle("Drone Camera Widget Test")
    window.setGeometry(100, 100, 800, 600)

    layout = QVBoxLayout(window)
    zmq_client = ZMQClient()  # Replace with your actual ZMQ address
    camera_widget = CameraWidget(video_client=zmq_client)
    layout.addWidget(camera_widget)

    window.show()
    sys.exit(app.exec())
