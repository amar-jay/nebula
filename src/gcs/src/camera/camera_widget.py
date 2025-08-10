import os
import sys
import time
import traceback

import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot
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
from qfluentwidgets import (
    Action,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    PrimaryPushButton,
)
from qfluentwidgets import PushButton as QPushButton
from qfluentwidgets import RoundMenu as QMenu

from src.controls.mavlink import mission_types
from src.gcs.src.camera.video_thread import VideoThread


class CameraWidget(QWidget):
    """Custom camera widget with self-contained RTSP video handling"""

    def __init__(self, parent=None, logger=None):
        super().__init__(parent)
        self.current_frame = None
        self.is_connected = False
        self.is_recording = False
        self.is_paused = False
        self.logger = logger if logger else print
        self.recording_filename = None
        video_urls = mission_types.get_video_urls()

        # RTSP URLs
        self.rtsp_processed_url = video_urls["processed_url"]
        self.rtsp_raw_url = video_urls["raw_url"]
        self.current_stream_type = "processed"  # Track current stream type

        # Video thread - will be created when connecting
        self.video_thread = None

        self.setup_ui()
        self.setup_style()

    def __del__(self):
        """Destructor - ensure cleanup happens"""
        try:
            if hasattr(self, "video_thread") and self.video_thread:
                if self.video_thread.isRunning():
                    self.video_thread.terminate()
                    self.video_thread.wait(1000)
        except Exception:
            pass  # Ignore errors in destructor

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

        # Connect button with dropdown menu for stream types
        self.connect_btn = PrimaryPushButton("Connect")
        self.connect_menu = QMenu("Connect", self)

        self.raw_connect_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "Raw Video Feed",
                triggered=lambda: self.connect_camera(_type="raw"),
            )
        )

        self.processed_connect_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "Processed Video Feed",
                triggered=lambda: self.connect_camera(_type="processed"),
            )
        )
        self.connect_btn.setMenu(self.connect_menu)

        # Disconnect button - always enabled to allow force disconnect
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_camera)
        self.disconnect_btn.setEnabled(True)  # Always allow disconnect

        # Record button
        self.record_btn = QPushButton("🔴")
        self.record_btn.setToolTip("Start/Stop Recording")
        self.record_btn.setFixedWidth(50)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(False)

        # Pause button
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setToolTip("Pause/Resume Recording")
        self.pause_btn.setFixedWidth(50)
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
        control_layout.addWidget(self.disconnect_btn)
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
            "src/gcs/assets/images/logo.png_"
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

    def _disconnect_video_signals(self):
        """Safely disconnect video thread signals."""
        if not self.video_thread:
            return

        try:
            # Only disconnect signals that were actually connected to this widget
            if hasattr(self.video_thread, "frame_ready"):
                try:
                    self.video_thread.frame_ready.disconnect(self.update_frame)
                except (AttributeError, RuntimeError, TypeError):
                    pass

            if hasattr(self.video_thread, "status_update"):
                try:
                    self.video_thread.status_update.disconnect(self.on_status_update)
                except (AttributeError, RuntimeError, TypeError):
                    pass

            # Don't try to disconnect fps_updated and error_occurred if they weren't connected
            # These signals are not connected in connect_camera method

        except Exception as e:
            print(f"Warning: Error disconnecting video signals: {e}")
            # Continue anyway, as this is just cleanup

    def connect_camera(self, _type: str = "processed"):
        """Connect to camera with specified stream type"""
        # Prevent multiple connection attempts
        if self.is_connected:
            self.logger("Camera already connected, disconnecting first", "warning")
            self.disconnect_camera()
            return

        try:
            # Disable UI elements during connection attempt
            self.connect_btn.setEnabled(False)
            self.record_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)

            # Disconnect any existing connections
            self._disconnect_video_signals()

            # Stop existing video thread if running
            if self.video_thread and self.video_thread.isRunning():
                self.video_thread.stop()
                self.video_thread = None

            # Select RTSP URL based on stream type
            rtsp_url = (
                self.rtsp_processed_url if _type == "processed" else self.rtsp_raw_url
            )
            self.current_stream_type = _type

            # Create new video thread
            self.video_thread = VideoThread(rtsp_url, logger=self.logger)

            # Connect signals
            self.video_thread.frame_ready.connect(self.update_frame)
            self.video_thread.status_update.connect(self.on_status_update)

            # Start video thread
            self.video_thread.start()

            self.is_connected = True
            self.status_label.setText(f"Camera Connecting ({_type})")

        except Exception as e:
            self.logger(f"Error connecting to camera: {e}", "error")
            traceback.print_exc()
            self.status_label.setText("Connection Failed")
            # Re-enable connect button on failure
            self.connect_btn.setEnabled(True)
            self.is_connected = False

    def on_status_update(self, message: str):
        """Handle status updates from video thread"""
        self.logger(f"Video status: {message}", "info")

        # Ignore status updates if we're not supposed to be connected
        if not self.is_connected:
            return

        if "connected successfully" in message.lower():
            self.status_label.setText(f"Camera Connected ({self.current_stream_type})")
            # Enable recording controls only after successful connection
            self.record_btn.setEnabled(True)
        elif "failed" in message.lower() or "error" in message.lower():
            self.status_label.setText("Connection Failed")
            # Re-enable connect button on failure
            self.connect_btn.setEnabled(True)
            self.is_connected = False
        else:
            self.status_label.setText(message)

    def disconnect_camera(self):
        """Disconnect from camera - always allowed for safety"""
        try:
            # Set flag first to prevent any new operations
            self.is_connected = False

            # Stop recording immediately if active
            if self.is_recording:
                self.is_recording = False
                self.is_paused = False

            # Update UI immediately to prevent user actions
            self.record_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.status_label.setText("Disconnecting...")

            # Disconnect all signals FIRST to prevent callbacks during cleanup
            self._disconnect_video_signals()

            # Then stop and cleanup video thread
            if self.video_thread:
                if self.video_thread.isRunning():
                    # Stop the thread
                    self.video_thread.stop()
                    # Wait for it to finish, but don't wait too long
                    if not self.video_thread.wait(5000):  # 5 second timeout
                        print("Warning: Force terminating video thread")
                        self.video_thread.terminate()
                        self.video_thread.wait(1000)

                # Clear the reference
                self.video_thread = None

            # Update UI to final state
            self.status_label.setText("Camera Disconnected")
            self.show_placeholder()
            self.connect_btn.setEnabled(True)

        except Exception as e:
            print(f"Error disconnecting camera: {e}")
        finally:
            # Ensure state is always clean regardless of errors
            self.is_connected = False
            self.is_recording = False
            self.is_paused = False
            self.connect_btn.setEnabled(True)
            self.record_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            if hasattr(self, "recording_indicator"):
                self.recording_indicator.hide()

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

            # Note: Recording is now handled by the video thread itself

    def toggle_recording(self):
        """Toggle video recording"""
        # Only allow if connected and UI is ready
        if not self.is_connected or not self.video_thread:
            self.logger("Cannot toggle recording: camera not connected", "warning")
            return

        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start video recording"""
        if not self.is_connected or not self.video_thread:
            self.logger("Cannot start recording: camera not connected", "warning")
            return

        if self.is_recording:
            self.logger("Recording already in progress", "warning")
            return

        try:
            # Create directory if it doesn't exist
            os.makedirs("recordings", exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.recording_filename = os.path.join(
                "recordings", f"drone_recording_{timestamp}.mp4"
            )

            # Start recording in the video thread
            self.video_thread.start_recording(self.recording_filename)

            self.is_recording = True
            self.record_btn.setText("🟥")
            self.pause_btn.setEnabled(True)
            self.recording_indicator.show()
            self.recording_indicator.setStyleSheet("color: #d83b01; font-size: 20px;")
            self.status_label.setText(f"Recording: {self.recording_filename}")

        except Exception as e:
            self.logger(f"Error starting recording: {e}", "error")
            traceback.print_exc()
            self.status_label.setText("Recording Failed")
            self.is_recording = False

    def stop_recording(self):
        """Stop video recording"""
        try:
            # Stop recording in the video thread
            if self.video_thread:
                self.video_thread.stop_recording()

            self.is_recording = False
            self.is_paused = False
            self.record_btn.setText("🔴")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸️")
            self.recording_indicator.hide()
            self.status_label.setText(
                "Recording Saved"
                if hasattr(self, "recording_filename") and self.recording_filename
                else f"Camera Connected ({self.current_stream_type})"
            )
        except Exception as e:
            self.logger(f"Error stopping recording: {e}", "error")
            traceback.print_exc()

    def toggle_pause(self):
        """Toggle recording pause"""
        if not self.is_recording or not self.video_thread:
            self.logger(
                "Cannot toggle pause: not recording or camera not connected", "warning"
            )
            return

        try:
            if self.is_paused:
                # Resume recording
                self.video_thread.resume_recording()
                self.is_paused = False
                self.pause_btn.setText("⏸️")
                self.status_label.setText("Recording Resumed")
            else:
                # Pause recording
                self.video_thread.pause_recording()
                self.is_paused = True
                self.pause_btn.setText("▶️")
                self.status_label.setText("Recording Paused")

        except Exception as e:
            self.logger(f"Error toggling pause: {e}", "error")
            traceback.print_exc()

    def closeEvent(self, event):
        """Clean up when widget is closed"""
        try:
            print("CameraWidget cleanup starting...")

            # Force stop everything immediately
            self.is_connected = False
            self.is_recording = False
            self.is_paused = False

            # Disconnect all signals first to prevent any callbacks
            if self.video_thread:
                self._disconnect_video_signals()

                # Stop the thread forcefully but safely
                if self.video_thread.isRunning():
                    print("Stopping video thread...")
                    self.video_thread.stop()

                    # Don't wait too long - this is cleanup
                    if not self.video_thread.wait(2000):  # 2 second timeout
                        print("Force terminating video thread during cleanup")
                        self.video_thread.terminate()
                        self.video_thread.wait(500)  # Short wait after terminate

                # Clear reference
                self.video_thread = None

            print("CameraWidget cleanup completed")

        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Don't prevent closing even if cleanup fails
        finally:
            # Always accept the close event
            event.accept()


# Example usage and testing
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create main window to test the widget
    window = QWidget()
    window.setWindowTitle("Drone Camera Widget Test")
    window.setGeometry(100, 100, 800, 600)

    layout = QVBoxLayout(window)

    # Create camera widget with custom RTSP URLs if needed
    camera_widget = CameraWidget()
    layout.addWidget(camera_widget)

    window.show()
    sys.exit(app.exec())
