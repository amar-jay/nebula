#!/usr/bin/env python3
import argparse
import logging
import threading
import time

import cv2
import numpy as np
import zmq

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zmq-video-client")


class ZMQVideoClient:
    """ZMQ client for receiving and displaying video streams"""

    def __init__(self, server_host: str = "localhost", video_port: int = 5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        # Connect to server
        self.server_address = f"tcp://{server_host}:{video_port}"
        logger.info(f"Connecting to {self.server_address}")
        self.socket.connect(self.server_address)

        # Subscribe to both video topics
        self.socket.setsockopt(zmq.SUBSCRIBE, b"video")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"processed_video")

        # Set receive timeout to non-blocking
        self.socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout

        self.running = False

        # Frame storage with locks
        self.frame_lock = threading.Lock()
        self.raw_frame = None
        self.processed_frame = None

        # Stats
        self.frames_received = 0
        self.raw_frames_received = 0
        self.processed_frames_received = 0

        logger.info(f"ZMQ Video Client initialized")

    def _decode_frame(self, frame_data: bytes) -> np.ndarray:
        """Decode JPEG frame data to OpenCV image"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            # Decode JPEG
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                logger.error("Failed to decode frame - cv2.imdecode returned None")
                return None

            # Check frame dimensions
            if frame.shape[0] == 0 or frame.shape[1] == 0:
                logger.error(f"Invalid frame dimensions: {frame.shape}")
                return None

            return frame
        except Exception as e:
            logger.error(f"Error decoding frame: {e}")
            return None

    def _receive_frames(self):
        """Receive and process video frames"""
        logger.info("Starting frame reception thread")

        while self.running:
            try:
                # Receive multipart message
                parts = self.socket.recv_multipart(zmq.NOBLOCK)

                if len(parts) != 2:
                    logger.warning(f"Expected 2 parts, got {len(parts)}")
                    continue

                topic, frame_data = parts

                # Decode frame
                frame = self._decode_frame(frame_data)
                if frame is None:
                    continue

                # Store frame based on topic
                with self.frame_lock:
                    if topic == b"video":
                        self.raw_frame = frame.copy()
                        self.raw_frames_received += 1
                        logger.debug(f"Received raw frame: {frame.shape}")
                    elif topic == b"processed_video":
                        self.processed_frame = frame.copy()
                        self.processed_frames_received += 1
                        logger.debug(f"Received processed frame: {frame.shape}")

                self.frames_received += 1

            except zmq.Again:
                # No message available - continue
                time.sleep(0.01)
                continue
            except Exception as e:
                logger.error(f"Error receiving frame: {e}")
                time.sleep(0.1)

        logger.info("Frame reception thread stopped")

    def _display_frames(self):
        """Display frames using OpenCV"""
        logger.info("Starting display loop")

        fps_count = 0
        fps_timer = time.time()
        last_frame_time = time.time()

        # Create windows
        cv2.namedWindow("Raw Video", cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow("Processed Video", cv2.WINDOW_AUTOSIZE)

        while self.running:
            try:
                current_time = time.time()
                display_updated = False

                with self.frame_lock:
                    # Display raw frame
                    if self.raw_frame is not None:
                        cv2.imshow("Raw Video", self.raw_frame)
                        display_updated = True

                    # Display processed frame
                    if self.processed_frame is not None:
                        cv2.imshow("Processed Video", self.processed_frame)
                        display_updated = True

                # Handle key events
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:  # 'q' or ESC
                    logger.info("Quit requested")
                    self.stop()
                    break
                elif key == ord("s"):  # 's' to save screenshots
                    self._save_screenshots()
                elif key == ord("r"):  # 'r' to reset windows
                    self._reset_windows()
                elif key == ord("i"):  # 'i' for info
                    self._print_info()

                # FPS tracking
                if display_updated:
                    fps_count += 1
                    if current_time - fps_timer > 5:
                        actual_fps = fps_count / (current_time - fps_timer)
                        logger.info(f"Display FPS: {actual_fps:.1f}")
                        logger.info(
                            f"Frames received - Raw: {self.raw_frames_received}, Processed: {self.processed_frames_received}"
                        )
                        fps_count = 0
                        fps_timer = current_time

                # Check if we're receiving frames
                if current_time - last_frame_time > 5:
                    logger.warning("No frames received in 5 seconds")
                    last_frame_time = current_time

                time.sleep(0.01)  # Small delay to prevent CPU spinning

            except Exception as e:
                logger.error(f"Error displaying frames: {e}")
                time.sleep(0.1)

        logger.info("Display loop stopped")

    def _save_screenshots(self):
        """Save current frames as screenshots"""
        timestamp = int(time.time())

        with self.frame_lock:
            if self.raw_frame is not None:
                filename = f"raw_frame_{timestamp}.jpg"
                cv2.imwrite(filename, self.raw_frame)
                logger.info(f"Saved raw frame: {filename}")

            if self.processed_frame is not None:
                filename = f"processed_frame_{timestamp}.jpg"
                cv2.imwrite(filename, self.processed_frame)
                logger.info(f"Saved processed frame: {filename}")

    def _reset_windows(self):
        """Reset OpenCV windows"""
        cv2.destroyAllWindows()
        cv2.namedWindow("Raw Video", cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow("Processed Video", cv2.WINDOW_AUTOSIZE)
        logger.info("Windows reset")

    def _print_info(self):
        """Print connection and frame info"""
        logger.info(f"Connected to: {self.server_address}")
        logger.info(f"Total frames received: {self.frames_received}")
        logger.info(f"Raw frames: {self.raw_frames_received}")
        logger.info(f"Processed frames: {self.processed_frames_received}")

        with self.frame_lock:
            if self.raw_frame is not None:
                logger.info(f"Raw frame shape: {self.raw_frame.shape}")
            if self.processed_frame is not None:
                logger.info(f"Processed frame shape: {self.processed_frame.shape}")

    def start(self):
        """Start the video client"""
        if self.running:
            logger.warning("Client already running")
            return

        # Test ZMQ connection
        logger.info("Testing ZMQ connection...")
        try:
            # Try to receive a message with short timeout
            test_socket = self.context.socket(zmq.SUB)
            test_socket.connect(self.server_address)
            test_socket.setsockopt(zmq.SUBSCRIBE, b"")
            test_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout

            try:
                test_socket.recv_multipart()
                logger.info("ZMQ connection successful")
            except zmq.Again:
                logger.warning("No messages received during connection test")

            test_socket.close()
        except Exception as e:
            logger.error(f"ZMQ connection test failed: {e}")

        self.running = True

        logger.info("Starting ZMQ Video Client...")
        logger.info("Controls:")
        logger.info("  'q' or ESC - Quit")
        logger.info("  's' - Save screenshots")
        logger.info("  'r' - Reset windows")
        logger.info("  'i' - Print info")

        try:
            # Start receiving frames in a separate thread
            self.receive_thread = threading.Thread(
                target=self._receive_frames, daemon=True
            )
            self.receive_thread.start()

            # Small delay to let receiver start
            time.sleep(0.5)

            # Display frames in main thread
            self._display_frames()

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the video client"""
        if not self.running:
            return

        logger.info("Stopping ZMQ Video Client...")
        self.running = False

        # Wait for receive thread to finish
        if hasattr(self, "receive_thread"):
            self.receive_thread.join(timeout=1.0)

        # Close OpenCV windows
        cv2.destroyAllWindows()

        # Close ZMQ socket
        self.socket.close()
        self.context.term()

        logger.info("ZMQ Video Client stopped")


def main():
    parser = argparse.ArgumentParser(description="ZMQ Video Client")
    parser.add_argument("--server-host", default="localhost", help="Server host")
    parser.add_argument("--video-port", type=int, default=5555, help="Video port")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and start client
    client = ZMQVideoClient(server_host=args.server_host, video_port=args.video_port)

    try:
        client.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.stop()


if __name__ == "__main__":
    main()
