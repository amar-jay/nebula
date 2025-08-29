import os
import sys
import time
import traceback

import cv2
import numpy as np

# pylint: disable=E0611,E1101
from PySide6.QtCore import Qt, QThread, Slot
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
from src.gcs.src.camera.video_thread import get_video_thread


class CameraWidget(QWidget):
    """Custom camera widget with persistent dual video threads"""

    def __init__(
        self,
        raw_url,
        processed_url,
        parent=None,
        logger=None,
    ):
        super().__init__(parent)
        self.current_frame = None
        self.is_connected = False
        self.is_recording = False
        self.is_paused = False
        self.logger = logger if logger else print
        self.recording_filename = None

        # URLs
        self.processed_url = processed_url
        self.raw_url = raw_url
        self.current_stream_type = None  # Track which stream is currently displayed

        # Persistent video threads - created once and reused
        self.raw_thread = None
        self.processed_thread = None
        self.active_thread = None  # Points to currently active thread

        self._setup_ui()

    def __del__(self):
        """Destructor - ensure cleanup happens"""
        try:
            self._cleanup_threads()
        except Exception:
            pass  # Ignore errors in destructor

    def _setup_ui(self):
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

        self.connect_menu.addAction(
            Action(
                icon=FIF.CONNECT,
                text="Raw Video Feed",
                triggered=lambda: self.connect_camera(_type="raw"),
            )
        )

        self.connect_menu.addAction(
            Action(
                icon=FIF.CONNECT,
                text="Processed Video Feed",
                triggered=lambda: self.connect_camera(_type="processed"),
            )
        )
        self.connect_btn.setMenu(self.connect_menu)

        # Disconnect button - always enabled to allow force disconnect
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_camera)
        self.disconnect_menu = QMenu("Disconnect", self)
        self.disconnect_btn.setEnabled(True)  # Always allow disconnect
        self.disconnect_menu.addAction(
            Action(
                icon=FIF.CONNECT,
                text="Normal",
                triggered=lambda: self.disconnect_camera(),  # pylint: disable=W0108
            )
        )

        self.disconnect_menu.addAction(
            Action(
                icon=FIF.CONNECT,
                text="Force",
                triggered=lambda: self.disconnect_camera(is_force=True),
            )
        )

        self.disconnect_btn.setMenu(self.disconnect_menu)

        # Reconnect button
        self.reconnect_btn = QPushButton("🔄")
        self.reconnect_btn.clicked.connect(self.reconnect_camera)
        self.reconnect_btn.setEnabled(False)

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
        # TODO: Faulty across all RTSP/ TCP/ IPC. DO NOT USE IT
        # control_layout.addWidget(self.reconnect_btn)
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

    def _setup_video_threads(self):
        """Setup persistent video threads for both raw and processed streams"""
        try:
            # Create raw video thread
            self.raw_thread = get_video_thread(
                self.raw_url, parent=self, logger=self.logger
            )
            self.raw_thread.frame_ready.connect(self._on_raw_frame)
            self.raw_thread.status_update.connect(
                lambda msg: self._on_status_update(msg, "raw")
            )

            # Create processed video thread
            self.processed_thread = get_video_thread(
                self.processed_url, parent=self, logger=self.logger
            )
            self.processed_thread.frame_ready.connect(self._on_processed_frame)
            self.processed_thread.status_update.connect(
                lambda msg: self._on_status_update(msg, "processed")
            )

            # Start both threads but they won't display until connected
            self.raw_thread.start()
            self.processed_thread.start()

            self.logger("Video threads initialized successfully", "info")

        except Exception as e:
            self.logger(f"Error setting up video threads: {e}", "error")
            traceback.print_exc()

    def _cleanup_threads(self):
        """Clean up both video threads"""
        threads = [("raw", self.raw_thread), ("processed", self.processed_thread)]

        for thread_name, thread in threads:
            if thread:
                try:
                    # Disconnect signals first
                    thread.frame_ready.disconnect()
                    thread.status_update.disconnect()
                except (AttributeError, RuntimeError, TypeError):
                    pass

                try:
                    thread.stop()  # Ensure thread's run loop exits
                    thread.wait(10000)  # Wait for thread to finish (max 10 seconds)
                    if thread.isRunning():
                        self.logger(
                            f"Force terminating {thread_name} thread", "warning"
                        )
                        thread.terminate()
                        thread.wait(1000)
                except Exception as e:
                    self.logger(f"Error stopping {thread_name} thread: {e}", "error")

        # Clear references
        self.raw_thread = None
        self.processed_thread = None
        self.active_thread = None

    def show_placeholder(self):
        """Show placeholder when camera is not connected"""
        placeholder = QPixmap(640, 480)
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

        scaled_placeholder = placeholder.scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(scaled_placeholder)

    def reconnect_camera(self):
        """Robustly reconnect both camera threads, cleaning up signals and threads first."""
        self.reconnect_btn.setEnabled(False)
        if not self.current_stream_type:
            self.logger("No previous stream type to reconnect to", "warning")
            return

        # Store the current stream type
        stream_type = self.current_stream_type

        # Disconnect current display
        self.disconnect_camera()

        QThread.msleep(100)  # 100 ms

        # Reconnect to the same stream type
        self.connect_camera(_type=stream_type)

        self.logger(f"Reconnecting to {stream_type} stream", "info")

    def connect_camera(self, _type: str = "processed"):
        """Switch to display specified stream type"""
        # Prevent switching during recording
        if self.is_recording:
            self.logger("Cannot switch streams during recording", "warning")
            return

        try:
            if self.raw_thread is None and self.processed_thread is None:
                self._setup_video_threads()

            # Disable UI elements during connection switch
            self.connect_btn.setEnabled(False)

            # Check if threads are available
            target_thread = self.raw_thread if _type == "raw" else self.processed_thread
            if not target_thread:
                self.logger(f"Error: {_type} thread not available", "error")
                self.connect_btn.setEnabled(True)
                return

            # Switch active thread
            self.active_thread = target_thread
            self.current_stream_type = _type
            self.is_connected = True

            # Update UI
            self.status_label.setText(f"Camera Connected ({_type})")
            self.record_btn.setEnabled(True)
            self.reconnect_btn.setEnabled(True)

            self.logger(f"Switched to {_type} video stream", "info")

        except Exception as e:
            self.logger(f"Error switching to {_type} stream: {e}", "error")
            traceback.print_exc()
            self.status_label.setText("Connection Failed")
            self.is_connected = False
        finally:
            self.connect_btn.setEnabled(True)

    @Slot(np.ndarray)
    def _on_raw_frame(self, frame):
        """Handle frame from raw video thread"""
        if self.is_connected and self.current_stream_type == "raw":
            self._update_display(frame)

    @Slot(np.ndarray)
    def _on_processed_frame(self, frame):
        """Handle frame from processed video thread"""
        # print(frame.shape, self.is_connected)
        if self.is_connected and self.current_stream_type == "processed":
            # print(frame.shape)
            self._update_display(frame)

    def _update_display(self, frame):
        """Update the camera display with new frame"""
        if frame is not None:
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

    def _on_status_update(self, message: str, stream_type: str):
        """Handle status updates from video threads"""
        # Only process status updates for the currently active stream
        if self.is_connected and self.current_stream_type == stream_type:
            self.logger(f"Video status ({stream_type}): {message}", "info")

            if "connected successfully" in message.lower():
                self.status_label.setText(f"Camera Connected ({stream_type})")
            elif "failed" in message.lower() or "error" in message.lower():
                self.status_label.setText("Connection Failed")
            else:
                # Only update status if it's not a routine message
                if "frame" not in message.lower():
                    self.status_label.setText(message)

    def disconnect_camera(self, is_force: bool = False):
        """Disconnect camera display (threads keep running in background)"""
        try:
            # Set flags
            self.is_connected = False
            self.current_stream_type = None
            self.active_thread = None

            # Stop recording if active
            if self.is_recording:
                self.stop_recording()

            if is_force:
                self._cleanup_threads()

            # Update UI
            self.reconnect_btn.setEnabled(False)
            self.record_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.status_label.setText("Camera Disconnected")
            self.show_placeholder()
            self.connect_btn.setEnabled(True)

            self.logger("Camera display disconnected", "info")

        except Exception as e:
            self.logger(f"Error disconnecting camera: {e}", "error")
        finally:
            # Ensure clean state
            self.is_connected = False
            self.is_recording = False
            self.is_paused = False
            self.connect_btn.setEnabled(True)
            if hasattr(self, "recording_indicator"):
                self.recording_indicator.hide()

    def toggle_recording(self):
        """Toggle video recording"""
        if not self.is_connected or not self.active_thread:
            self.logger("Cannot toggle recording: camera not connected", "warning")
            return

        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start video recording"""
        if not self.is_connected or not self.active_thread:
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
                "recordings",
                f"drone_recording_{self.current_stream_type}_{timestamp}.mp4",
            )

            # Start recording in the active video thread
            self.active_thread.start_recording(self.recording_filename)

            self.is_recording = True
            self.record_btn.setText("🟥")
            self.pause_btn.setEnabled(True)
            self.recording_indicator.show()
            self.recording_indicator.setStyleSheet("color: #d83b01; font-size: 20px;")
            self.status_label.setText(
                f"Recording: {os.path.basename(self.recording_filename)}"
            )

        except Exception as e:
            self.logger(f"Error starting recording: {e}", "error")
            traceback.print_exc()
            self.status_label.setText("Recording Failed")
            self.is_recording = False

    def stop_recording(self):
        """Stop video recording"""
        try:
            # Stop recording in the active thread
            if self.active_thread:
                self.active_thread.stop_recording()

            self.is_recording = False
            self.is_paused = False
            self.record_btn.setText("🔴")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸️")
            self.recording_indicator.hide()

            status_text = "Recording Saved"
            if self.is_connected:
                status_text = f"Camera Connected ({self.current_stream_type})"
            self.status_label.setText(status_text)

        except Exception as e:
            self.logger(f"Error stopping recording: {e}", "error")
            traceback.print_exc()

    def toggle_pause(self):
        """Toggle recording pause"""
        if not self.is_recording or not self.active_thread:
            self.logger(
                "Cannot toggle pause: not recording or camera not connected", "warning"
            )
            return

        try:
            if self.is_paused:
                # Resume recording
                self.active_thread.resume_recording()
                self.is_paused = False
                self.pause_btn.setText("⏸️")
                self.status_label.setText("Recording Resumed")
            else:
                # Pause recording
                self.active_thread.pause_recording()
                self.is_paused = True
                self.pause_btn.setText("▶️")
                self.status_label.setText("Recording Paused")

        except Exception as e:
            self.logger(f"Error toggling pause: {e}", "error")
            traceback.print_exc()

    def closeEvent(self, event):
        """Clean up when widget is closed"""
        try:
            self.logger("CameraWidget cleanup starting...", "info")

            # Force stop everything immediately
            self.is_connected = False
            self.is_recording = False
            self.is_paused = False

            # Clean up threads
            self._cleanup_threads()

            self.logger("CameraWidget cleanup completed", "info")

        except Exception as e:
            self.logger(f"Error during cleanup: {e}", "error")
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

    config = mission_types.get_config()
    # Create camera widget with custom URLs if needed
    camera_widget = CameraWidget(
        processed_url=config.video_output,
        raw_url=config.video_source,
    )

    layout.addWidget(camera_widget)

    window.show()
    sys.exit(app.exec())
