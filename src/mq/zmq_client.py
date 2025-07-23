import logging
import time

import cv2
import numpy as np
import zmq
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

# Usage example in a PySide6 application:
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

logger = logging.getLogger(__name__)


class ZMQVideoThread(QThread):
    """QThread for receiving ZMQ video frames"""

    # Signals for communicating with the main thread
    frame_received = Signal(np.ndarray)  # Raw video frame
    processed_frame_received = Signal(np.ndarray)  # Processed frame
    fps_updated = Signal(float)  # FPS information
    error_occurred = Signal(str)  # Error messages

    def __init__(self, server_ip="localhost", video_port=5555, parent=None):
        super().__init__(parent)
        self.server_ip = server_ip
        self.video_port = video_port
        self.running = False

        # ZMQ setup
        self.context = None
        self.video_socket = None

    def setup_zmq(self):
        """Initialize ZMQ connection"""
        try:
            self.context = zmq.Context()
            self.video_socket = self.context.socket(zmq.SUB)
            self.video_socket.connect(f"tcp://{self.server_ip}:{self.video_port}")
            self.video_socket.setsockopt_string(
                zmq.SUBSCRIBE, ""
            )  # Subscribe to all topics
            logger.info(
                f"Connected to video stream at {self.server_ip}:{self.video_port}"
            )
        except Exception as e:
            self.error_occurred.emit(f"Failed to setup ZMQ: {str(e)}")
            raise

    def run(self):
        """Main thread execution - receives video frames"""
        try:
            self.setup_zmq()
            self.running = True

            fps_count = 0
            fps_timer = time.time()

            logger.info("Video receiver thread started")

            while self.running:
                try:
                    # Poll with timeout to make loop interruptible
                    if self.video_socket.poll(timeout=100) != 0:  # 100ms timeout
                        # Receive frame data
                        topic, frame_data = self.video_socket.recv_multipart()

                        # Decode frame
                        jpg_buffer = np.frombuffer(frame_data, dtype=np.uint8)
                        frame = cv2.imdecode(jpg_buffer, cv2.IMREAD_COLOR)

                        if frame is not None:
                            # Emit appropriate signal based on topic
                            if topic == b"processed_video":
                                self.processed_frame_received.emit(frame)
                            elif topic == b"video":
                                self.frame_received.emit(frame)
                            else:
                                logger.warning(f"Unknown topic received: {topic}")

                        # FPS calculation
                        fps_count += 1
                        curr_time = time.time()
                        if curr_time - fps_timer > 10:  # Update FPS every 10 seconds
                            fps = fps_count / 10
                            self.fps_updated.emit(fps)
                            fps_count = 0
                            fps_timer = curr_time

                except zmq.ZMQError as e:
                    if self.running:  # Only log if we're still supposed to be running
                        self.error_occurred.emit(f"ZMQ error: {str(e)}")
                    time.sleep(0.1)
                except Exception as e:
                    if self.running:
                        self.error_occurred.emit(f"Video receiver error: {str(e)}")
                    time.sleep(0.1)

        except Exception as e:
            self.error_occurred.emit(f"Critical error in video thread: {str(e)}")
        finally:
            self.cleanup_zmq()
            logger.info("Video receiver thread stopped")

    def stop(self):
        """Stop the video receiving thread"""
        self.running = False
        self.wait(2000)  # Wait up to 2 seconds for thread to finish

    def cleanup_zmq(self):
        """Clean up ZMQ resources"""
        if self.video_socket:
            self.video_socket.close()
        if self.context:
            self.context.term()


class ZMQClient:
    """Simplified ZMQ client for PySide6 applications"""

    def __init__(self, server_ip="localhost", video_port=5555, control_port=5556):
        self.server_ip = server_ip
        self.control_port = control_port

        # Video thread
        self.video_thread = ZMQVideoThread(server_ip, video_port)

        # Control socket setup
        self.context = zmq.Context()
        self.control_socket = self.context.socket(zmq.REQ)
        self.control_socket.connect(f"tcp://{server_ip}:{control_port}")
        self.control_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout

        # Current frames (thread-safe through Qt signals)
        self.current_frame = None
        self.current_processed_frame = None

        # Connect signals
        self.video_thread.frame_received.connect(self._on_frame_received)
        self.video_thread.processed_frame_received.connect(
            self._on_processed_frame_received
        )
        self.video_thread.fps_updated.connect(self._on_fps_updated)
        self.video_thread.error_occurred.connect(self._on_error)

        logger.info(f"ZMQ Video Client initialized for {server_ip}")

    def _on_frame_received(self, frame):
        """Handle raw video frame reception"""
        self.current_frame = frame

    def _on_processed_frame_received(self, frame):
        """Handle processed frame reception"""
        self.current_processed_frame = frame

    def _on_fps_updated(self, fps):
        """Handle FPS updates"""
        logger.info(f"Video FPS: {fps:.2f}")

    def _on_error(self, error_msg):
        """Handle errors from video thread"""
        logger.error(f"Video thread error: {error_msg}")

    def start(self):
        """Start video reception"""
        if not self.video_thread.isRunning():
            self.video_thread.start()
            logger.info("Video client started")

    def stop(self):
        """Stop video reception and cleanup"""
        try:
            self.video_thread.stop()

            # Cleanup control socket
            self.control_socket.close()
            self.context.term()
        except:
            pass

        logger.info("Video client stopped")

    def send_command(self, command) -> str:
        """Send control command to server"""
        if not self.control_socket:
            logger.info("not connected")
            return None
        try:
            logger.info(f"Sending command: {command}")
            self.control_socket.send_string(
                command.name if hasattr(command, "name") else str(command)
            )
            response = self.control_socket.recv_string()
            logger.info(f"Received response: {response}")
            return response
        except zmq.ZMQError as e:
            logger.error(f"Failed to send command: {e}")
            return None

    def get_current_frame(self):
        """Get the latest raw frame"""
        return self.current_frame

    def get_current_processed_frame(self):
        """Get the latest processed frame"""
        return self.current_processed_frame


class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.label = QLabel()
        self.setCentralWidget(self.label)

        # Initialize video client
        self.video_client = ZMQClient()
        self.video_client.video_thread.frame_received.connect(self.update_display)

        self.video_client.start()

    def update_display(self, frame):
        # Convert OpenCV frame to QImage and display
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        ).rgbSwapped()
        self.label.setPixmap(QPixmap.fromImage(qt_image))

    def closeEvent(self, event):
        self.video_client.stop()
        event.accept()


def main():
    """Main application entry point"""
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show main window
    window = VideoWindow()
    window.show()

    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
