#!/usr/bin/env python3
import argparse
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np
import zmq

from .messages import ZMQTopics

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zmq-video-client")


class Client:
    def __init__(
        self,
        server_ip: str = "localhost",
        video_port: int = 5555,
        control_port: int = 5556,
    ):
        """
        Initialize the ZMQ Video Client

        Args:
            server_ip: IP address of the video server
            video_port: Port for video frame subscription
            control_port: Port for sending control commands
        """
        self.context = zmq.Context()
        self.server_ip = server_ip

        # Video subscriber socket (PUB-SUB pattern)
        self.video_socket = self.context.socket(zmq.SUB)
        self.video_socket.connect(f"tcp://{server_ip}:{video_port}")
        self.video_socket.setsockopt_string(
            zmq.SUBSCRIBE, ""
        )  # Subscribe to all topics

        # Control socket (REQ-REP pattern)
        self.control_socket = self.context.socket(zmq.REQ)
        self.control_socket.connect(f"tcp://{server_ip}:{control_port}")
        self.control_socket.setsockopt(
            zmq.RCVTIMEO, 5000
        )  # 5 seconds timeout for control responses

        # Flags for threads
        self.running = False
        self.video_thread = None

        # Frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # processed frame storage
        self.processed_frame = None
        self.processed_frame_lock = threading.Lock()

        logger.info(
            f"Client initialized, connecting to {server_ip} on video port {video_port} and control port {control_port}"
        )

    def video_receiver_loop(self):
        """Video receiving loop - runs in a separate thread"""
        logger.info("Video receiver started")

        fps_count = 0
        fps_timer = time.time()

        while self.running:
            try:
                # Use poll with timeout to make the loop interruptible
                if self.video_socket.poll(timeout=100) != 0:  # 100ms timeout
                    # Receive and decode video frame
                    topic, frame_data = self.video_socket.recv_multipart()

                    # Convert the frame data back to an image
                    jpg_buffer = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(jpg_buffer, cv2.IMREAD_COLOR)

                    # Update current frame with thread safety
                    if topic == b"processed_video":
                        with self.processed_frame_lock:
                            self.processed_frame = frame
                    elif topic == b"video":
                        with self.frame_lock:
                            self.current_frame = frame
                    else:
                        logger.warning(f"Unknown topic received: {topic}")

                    # FPS calculation
                    # fps_count += 1
                    # if time.time() - fps_timer > 10:  # Log FPS every 5 seconds
                    # 	logger.info(f"Receiving video at {fps_count / 5:.2f} FPS")
                    # 	fps_count = 0
                    # 	fps_timer = time.time()
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error in video receiver: {e}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in video receiver: {e}")
                time.sleep(0.1)

    def send_command(self, command: ZMQTopics) -> Optional[str]:
        try:
            # logger.info(f"Sending command: {command}")
            self.control_socket.send_string(command.name)
            response = self.control_socket.recv_string()
            # logger.info(f"Received response: {response}")
            return response
        except zmq.ZMQError as e:
            logger.error(f"Failed to send command: {e}")
            return None

    def get_current_processed_frame(self) -> Optional[np.ndarray]:
        with self.processed_frame_lock:
            if self.processed_frame is not None:
                return self.processed_frame.copy()
            return None

    def get_current_frame(self) -> Optional[np.ndarray]:
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def start(self):
        """Start the client"""
        if self.running:
            logger.warning("Client is already running")
            return

        self.running = True

        # Start video receiver thread
        self.video_thread = threading.Thread(target=self.video_receiver_loop)
        self.video_thread.daemon = True
        self.video_thread.start()

        logger.info("Client started")

    def stop(self):
        """Stop the client"""
        logger.info("Stopping client...")
        self.running = False

        if self.video_thread:
            self.video_thread.join(timeout=2.0)

        # Clean up ZMQ resources
        self.video_socket.close()
        self.control_socket.close()
        self.context.term()

        logger.info("Client stopped")

    def get_video_stream(self, imshow_func=None):
        frame = self.get_current_frame()
        if frame is not None:
            if imshow_func is not None:
                imshow_func(frame)
            else:
                cv2.imshow("ZMQ Video Client", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    return

    def get_processed_stream(self, imshow_func=None):
        frame = self.get_current_processed_frame()
        if frame is not None:
            if imshow_func is not None:
                imshow_func(frame)
            else:
                cv2.imshow("Processed Video", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                return


def main():
    from src.controls.mavlink.ardupilot import ArdupilotConnection

    parser = argparse.ArgumentParser(
        description="ZMQ Video Client with Control Interface"
    )
    parser.add_argument(
        "--server", type=str, default="10.42.0.189", help="Server IP address"
    )
    parser.add_argument(
        "--video-port", type=int, default=5555, help="Port for video subscription"
    )
    parser.add_argument(
        "--control-port", type=int, default=5556, help="Port for control commands"
    )
    args = parser.parse_args()

    print("ZMQ Video Client with Control Interface\n")
    connection = ArdupilotConnection("tcp:10.42.0.189:16550")
    print("ZMQ Video Client with Control Interface\n")
    client = Client(
        server_ip=args.server,
        video_port=args.video_port,
        control_port=args.control_port,
    )

    def video_thread_func(client):
        while client.running:
            client.get_video_stream()
            client.get_processed_stream()
            time.sleep(0.01)

    video_thread = threading.Thread(
        target=video_thread_func, args=(client,), daemon=True
    )

    try:
        client.start()
        video_thread.start()
        logger.info(
            "Client running. Press 'q' to quit, 'r' to raise hook, 'd' to drop hook"
        )

        # Display loop for video frames and handle keyboard commands
        while True:
            _inp = input("Enter command (p/o/r/d/q/a/t/l/s): ").strip().lower()
            if _inp == "p":
                response = client.send_command(ZMQTopics.PICK_LOAD)
                logger.info(f"Response: {response}")
            elif _inp == "o":
                response = client.send_command(ZMQTopics.DROP_LOAD)
                logger.info(f"Response: {response}")
            if _inp == "r":
                response = client.send_command(ZMQTopics.RAISE_HOOK)
                logger.info(f"Response: {response}")
            elif _inp == "d":
                response = client.send_command(ZMQTopics.DROP_HOOK)
                logger.info(f"Response: {response}")
            elif _inp == "q":
                break
            elif _inp == "a":
                connection.arm()
            elif _inp == "t":
                connection.takeoff(10)
            elif _inp == "l":
                connection.land()
            elif _inp == "g":
                lat, lon, alt = connection.get_current_gps_location()
                print(f"Current GPS Location: lat={lat}, lon={lon}, alt={alt}")
            elif _inp == "s":
                response = client.send_command(ZMQTopics.STATUS)
                logger.info(f"Response: {response}")
            time.sleep(0.01)  # Small delay to prevent CPU usage spike

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        client.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
