import time

import cv2
import numpy as np

# pylint: disable=E0611
from PySide6.QtCore import QThread, Signal


class VideoThread(QThread):
    """QThread for reading video from RTSP streams"""

    # Signals for communicating with the main thread
    frame_ready = Signal(np.ndarray)  # Video frame
    status_update = Signal(str)  # Status messages
    fps_updated = Signal(float)  # FPS information
    error_occurred = Signal(str)  # Error messages

    def __init__(self, rtsp_url, parent=None, logger=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.running = False
        self.cap = None
        self.logger = logger if logger else print

        # Video recording attributes
        self.video_writer = None
        self.is_recording = False
        self.is_paused = False
        self.recording_filepath = None

    def run(self):
        """Main video capture loop for RTSP streams with robust reconnection"""
        self.running = True
        retry_count = 0
        max_retries = 50  # Increased for better persistence
        consecutive_failures = 0
        last_successful_frame_time = time.time()

        # Try both secure and non-secure RTSP if original URL fails
        urls_to_try = [self.rtsp_url]
        if self.rtsp_url.startswith("rtsps://"):
            # Add fallback to non-secure RTSP
            fallback_url = self.rtsp_url.replace("rtsps://", "rtsp://")
            urls_to_try.append(fallback_url)

        while self.running and retry_count < max_retries:
            # Check if we should stop before attempting connection
            if not self.running:
                return  # Exit immediately

            current_url = urls_to_try[retry_count % len(urls_to_try)]

            try:
                # Open RTSP stream
                self.status_update.emit(f"Attempting to connect to RTSP: {current_url}")
                self.cap = cv2.VideoCapture(current_url)

                # Check if we should stop after creating capture
                if not self.running:
                    if self.cap is not None:
                        try:
                            if hasattr(self.cap, "isOpened") and self.cap.isOpened():
                                self.cap.release()
                        except Exception:
                            pass
                        self.cap = None
                    return  # Exit immediately

                # Try to read a test frame to verify connection
                if not self.cap.isOpened():
                    self.status_update.emit(
                        f"Failed to open RTSP stream: {current_url}"
                    )
                    retry_count += 1
                    wait_time = min(
                        2 ** min(retry_count, 5), 30
                    )  # Exponential backoff, max 30s
                    self.status_update.emit(
                        f"Retrying in {wait_time} seconds... (attempt {retry_count}/{max_retries})"
                    )
                    # Sleep in smaller increments to respond to stop requests faster
                    for _ in range(wait_time * 10):  # 100ms increments
                        if not self.running:
                            return
                        self.msleep(100)
                    continue

                # Test read to ensure stream is working
                test_ret, test_frame = self.cap.read()
                if not test_ret or test_frame is None:
                    self.status_update.emit(
                        f"RTSP stream opened but no frames available from {current_url}"
                    )
                    if (
                        self.cap is not None
                        and hasattr(self.cap, "isOpened")
                        and self.cap.isOpened()
                    ):
                        self.cap.release()
                    self.cap = None
                    retry_count += 1
                    wait_time = min(2 ** min(retry_count, 5), 30)
                    self.msleep(wait_time * 1000)
                    continue

                self.status_update.emit(
                    f"RTSP stream connected successfully: {current_url}"
                )
                retry_count = 0  # Reset retry count on success
                consecutive_failures = 0
                last_successful_frame_time = time.time()

                fps_count = 0
                fps_timer = time.time()

                # Main frame reading loop
                while self.running:
                    # Check if we should exit before each frame read
                    if not self.running:
                        break

                    try:
                        # Check if cap is still valid before reading
                        if self.cap is None or not hasattr(self.cap, "read"):
                            break

                        ret, frame = self.cap.read()
                        if ret and frame is not None:
                            # Check again after getting frame, before emitting
                            if not self.running:
                                break

                            self.frame_ready.emit(frame)
                            consecutive_failures = 0
                            last_successful_frame_time = time.time()

                            # Video recording logic
                            if (
                                self.is_recording
                                and not self.is_paused
                                and self.running
                            ):
                                # Setup video writer on first frame
                                if self.video_writer is None:
                                    self._setup_video_writer(frame.shape)

                                # Write frame if writer is ready
                                if self.video_writer:
                                    self.video_writer.write(frame)

                            # FPS calculation (only if still running)
                            if self.running:
                                fps_count += 1
                                current_time = time.time()
                                if current_time - fps_timer >= 1.0:
                                    fps = fps_count / (current_time - fps_timer)
                                    self.fps_updated.emit(fps)
                                    fps_count = 0
                                    fps_timer = current_time

                            # cv2.waitKey(1)
                            self.msleep(1)  # ~30 FPS
                        else:
                            consecutive_failures += 1
                            current_time = time.time()

                            # Check if we've been failing for too long
                            if (
                                consecutive_failures > 10
                                or (current_time - last_successful_frame_time) > 10
                            ):
                                if self.running:  # Only emit if still running
                                    self.status_update.emit(
                                        "Too many consecutive frame failures, reconnecting..."
                                    )
                                break

                            # Small delay before next frame attempt
                            self.msleep(100)
                    except Exception as frame_error:
                        # Handle frame reading errors specifically
                        consecutive_failures += 1
                        if self.running:  # Only emit if still running
                            self.status_update.emit(
                                f"Frame reading error: {frame_error}"
                            )
                        if consecutive_failures > 5:
                            if self.running:
                                self.status_update.emit(
                                    "Too many frame reading errors, reconnecting..."
                                )
                            break
                        self.msleep(200)  # Wait a bit longer on error

            except Exception as e:
                self.status_update.emit(f"RTSP connection error: {e}")
                retry_count += 1
                wait_time = min(2 ** min(retry_count, 5), 30)
                self.status_update.emit(f"Will retry in {wait_time} seconds...")
                # Sleep in smaller increments to respond to stop requests faster
                for _ in range(wait_time * 10):  # 100ms increments
                    if not self.running:
                        return
                    self.msleep(100)
            finally:
                # Cleanup: safely release the capture object
                if self.cap is not None:
                    try:
                        if hasattr(self.cap, "isOpened") and self.cap.isOpened():
                            self.cap.release()
                    except Exception as e:
                        print(f"Warning: Error releasing capture in finally block: {e}")
                    finally:
                        self.cap = None

        if retry_count >= max_retries:
            self.status_update.emit(
                f"Max retries ({max_retries}) reached for RTSP stream"
            )
        else:
            self.status_update.emit("RTSP video thread stopped")

    def stop(self):
        """Stop the video thread"""
        self.running = False

        if self.is_recording:  # Stop any ongoing recording first
            self.stop_recording()

        # Force release capture BEFORE trying to quit the thread
        if self.cap is not None:
            try:
                self.msleep(200)  # Give current operation time to complete
                if hasattr(self.cap, "isOpened") and self.cap.isOpened():
                    self.cap.release()
            except Exception as e:
                print(f"Warning: Error releasing video capture: {e}")
            finally:
                self.cap = None  # Always set to None to prevent further access

        # Now quit the thread
        if self.isRunning():
            self.quit()  # Request thread to quit
            # Wait for thread to finish naturally
            if not self.wait(3000):  # 3 second timeout
                print(
                    "Warning: Video thread did not stop gracefully, forcing termination"
                )
                self.terminate()  # Force terminate as last resort
                self.wait(1000)  # Give it a short time to clean up

    def start_recording(self, filepath: str):
        """Start video recording"""
        if self.is_recording:
            self.logger("Recording already in progress", "warning")
            return

        try:
            # Create video writer - we'll get frame size from first frame
            self.recording_filepath = filepath
            self.is_recording = True
            self.is_paused = False
            self.logger(f"Recording started: {filepath}", "info")
        except Exception as e:
            self.logger(f"Failed to start recording: {e}", "error")
            self.is_recording = False

    def stop_recording(self):
        """Stop video recording"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_paused = False

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.logger(f"Recording stopped: {self.recording_filepath}", "info")
        self.recording_filepath = None

    def pause_recording(self):
        """Pause video recording"""
        if self.is_recording:
            self.is_paused = True
            self.logger("Recording paused", "info")

    def resume_recording(self):
        """Resume video recording"""
        if self.is_recording:
            self.is_paused = False
            self.logger("Recording resumed", "info")

    def _setup_video_writer(self, frame_shape):
        """Setup video writer with frame dimensions"""
        if self.video_writer is None and self.is_recording:
            height, width = frame_shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(
                self.recording_filepath, fourcc, 20.0, (width, height)
            )
