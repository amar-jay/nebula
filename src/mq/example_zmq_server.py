#!/usr/bin/env python3
import argparse
import logging
import socket
import threading
import time
from typing import Tuple

import cv2
import numpy as np
import zmq

from src.controls.detection import yolo
from src.controls.mavlink import ardupilot, gz, mission_types
from src.mq.messages import ZMQTopics

parser = argparse.ArgumentParser(description="ZMQ Video Server with Control Interface")
parser.add_argument(
    "--is-simulation", action="store_true", help="Run in simulation mode"
)

parser.add_argument(
    "--video-port", type=int, default=5555, help="Port for video publishing"
)
parser.add_argument(
    "--control-port", type=int, default=5556, help="Port for control commands"
)
parser.add_argument(
    "--video-source", default=0, help="Video source (device ID or file path)"
)
args = parser.parse_args()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zmq-video-server")

IS_SIMULATION = args.is_simulation

# Configuration
if IS_SIMULATION:
    CONNECTION_STRING = "udp:127.0.0.1:14550"
else:
    CONNECTION_STRING = "/dev/ttyUSB0"  # Change to your serial port

# BAUD_RATE = 57600  # Change to your baud rate
TCP_HOST = "0.0.0.0"  # Listen on all interfaces
TCP_PORT = 16550  # Standard MAVLink port

try:
    connection = ardupilot.ArdupilotConnection(connection_string=CONNECTION_STRING)
except ConnectionError:
    logger.error(f"Failed to connect to MAVLink at {CONNECTION_STRING}.")
    exit(1)

logger.info("mavlink connection established")

# List to keep track of client connections
clients = []
clients_lock = threading.Lock()

# Set up TCP server
tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp_server.bind((TCP_HOST, TCP_PORT))
tcp_server.listen(5)  # Allow up to 5 connections
logger.info(f"TCP server listening on {TCP_HOST}:{TCP_PORT}")


def handle_client(client_socket, client_address):
    logger.info(f"New client connected: {client_address}")

    try:
        while True:
            # Read from TCP client
            try:
                data = client_socket.recv(1024)
                if not data:
                    break  # Client disconnected

                # Forward from TCP client to serial
                connection.master.write(data)
            except Exception as e:
                logger.error(f"Error reading from client {client_address}: {e}")
                break
    finally:
        with clients_lock:
            clients.remove(client_socket)
        client_socket.close()
        logger.info(f"Client disconnected: {client_address}")


def accept_clients():
    while True:
        try:
            client_socket, client_address = tcp_server.accept()
            with clients_lock:
                clients.append(client_socket)

            # Start a new thread to handle this client
            client_thread = threading.Thread(
                target=handle_client, args=(client_socket, client_address), daemon=True
            )
            client_thread.start()
        except Exception as e:
            logger.error(f"Error accepting client: {e}")
            time.sleep(1)  # Avoid CPU spinning on error


def forward_from_serial_to_tcp():
    while True:
        try:
            # Wait for a message from the serial connection
            msg = connection.master.recv_match(blocking=True)
            if msg is not None:
                # Convert the message back to bytes
                msg_bytes = msg.get_msgbuf()

                # Send to all TCP clients
                with clients_lock:
                    disconnected_clients = []
                    for client in clients:
                        try:
                            client.send(msg_bytes)
                        except Exception:
                            # Mark client for removal
                            disconnected_clients.append(client)

                    # Remove disconnected clients
                    for client in disconnected_clients:
                        clients.remove(client)
                        try:
                            client.close()
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error in serial to TCP forwarding: {e}")
            time.sleep(0.1)  # Avoid CPU spinning on error


class ZMQServer:
    def __init__(
        self,
        video_port: int = 5555,
        control_port: int = 5556,
        video_source: int = 0,
        is_simulation: bool = False,
    ):
        """
        video_port: Port for video frame publishing
        control_port: Port for receiving control commands
        video_source: Camera device ID or video file path
        """
        self.context = zmq.Context()

        # Video publisher socket (PUB-SUB pattern)
        self.video_socket = self.context.socket(zmq.PUB)
        self.video_socket.bind(f"tcp://*:{video_port}")

        # Control socket (REQ-REP pattern)
        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(f"tcp://*:{control_port}")

        # Video capture
        self.cap = None
        self.video_source = video_source

        # Hook state
        self.hook_state = "dropped"  # "raised" or "dropped"

        # Flags for threads
        self.running = False
        self.video_thread = None
        self.control_thread = None

        self.object_classes = ["helipad", "tank" if IS_SIMULATION else "real_tank"]
        self.prev_attitude = None

        # Enable video streaming for simulation

        if IS_SIMULATION:
            logger.info("Enabling video streaming")
            done = gz.enable_streaming(
                world="delivery_runway",
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
            )
            logger.info("Enabling streaming")
            if not done:
                logger.error("❌ Failed to enable streaming.")
                return
            camera_intrinsics = gz.get_camera_intrinsics(
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
                world="delivery_runway",
            )
        else:
            camera_intrinsics = mission_types.get_camera_intrinsics()

        if camera_intrinsics is None:
            logger.error("❌ Failed to get camera intrinsics.")
            return
        camera_intrinsics = camera_intrinsics.get("camera_intrinsics", None)

        self.tracker = yolo.YoloObjectTracker(
            K=camera_intrinsics,
            model_path="src/controls/detection/best.pt",
        )
        logger.info(
            "Server initialized with video port %d and control port %d",
            video_port,
            control_port,
        )

    def start_capture(self) -> bool:
        """Start the video capture"""
        try:
            if IS_SIMULATION:
                self.cap = gz.GazeboVideoCapture()
            else:
                self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source {self.video_source}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error starting video capture: {e}")
            return False

    def encode_frame(self, frame: np.ndarray, _type="raw") -> Tuple[bytes, bytes]:
        """
        Encode a frame to JPEG and prepare it for sending

        Returns:
            Tuple of (topic, jpeg_bytes)
        """
        if _type == "raw":
            topic = b"video"
        else:
            topic = b"processed_video"
        _, jpeg_frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return topic, jpeg_frame.tobytes()

    def video_publisher_loop(self):
        """Video publishing loop - runs in a separate thread"""
        if not self.start_capture():
            return

        logger.info("Video publishing started")
        fps_count = 0
        fps_timer = time.time()

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to capture frame, restarting capture")
                if not self.start_capture():  # Try to restart capture
                    time.sleep(1)  # Wait before retry
                    continue
                continue

            # Send the frame
            topic, encoded_frame = self.encode_frame(frame)
            self.video_socket.send_multipart([topic, encoded_frame])

            # send the processed frame to the serial connection
            drone_position = connection.get_current_gps_location(relative=False)
            if drone_position is None:
                logger.error("Failed to get drone GPS position")
                continue
            curr_position = (drone_position[0], drone_position[1], drone_position[2][1])
            drone_attitude = connection.get_current_attitude()
            if drone_attitude is None and self.prev_attitude is None:
                logger.error("Failed to get drone attitude")
                continue
            if drone_attitude is None:
                drone_attitude = self.prev_attitude
                logger.warning("Using previous attitude as current attitude")
            else:
                logger.info(f"Current attitude: {drone_attitude}")

            processed_frame, gps_coords, pixel_coords = self.tracker.process_frame(
                frame=frame,
                drone_gps=curr_position,
                drone_attitude=drone_attitude,
                ground_level_masl=drone_position[2][1] - drone_position[2][0],
                object_classes=self.object_classes,
            )
            self.gps_coordinates = gps_coords
            self.pixel_coordinates = pixel_coords

            # Encode the processed frame
            topic, processed_encoded_frame = self.encode_frame(
                processed_frame, _type="processed"
            )
            self.video_socket.send_multipart([topic, processed_encoded_frame])

            # FPS calculation
            fps_count += 1
            if time.time() - fps_timer > 10:  # Log FPS every 5 seconds
                logger.info(f"Publishing video at {fps_count / 5:.2f} FPS")
                fps_count = 0
                fps_timer = time.time()

            # Small sleep to avoid maxing out CPU
            time.sleep(0.001)

        # Cleanup
        if self.cap:
            self.cap.release()
        logger.info("Video publishing stopped")

    def handle_command(self, command: str) -> str:
        command = command.strip()

        if command == ZMQTopics.DROP_LOAD.name:
            return "ACK: Load dropped"
        elif command == ZMQTopics.PICK_LOAD.name:
            return "ACK: Load picked"
        elif command == ZMQTopics.RAISE_HOOK.name:
            if self.hook_state == "raised":
                return "ACK: Hook already raised"
            else:
                self.hook_state = "raised"
                return "ACK: Hook raised"

        elif command == ZMQTopics.DROP_HOOK.name:
            if self.hook_state == "dropped":
                return "ACK: Hook already dropped"
            else:
                self.hook_state = "dropped"
                return "ACK: Hook dropped"

        elif command == ZMQTopics.STATUS.name:
            return f"ACK: Hook is {self.hook_state}"
        elif command == ZMQTopics.HELIPAD_GPS.name:
            if hasattr(self, "gps_coordinates"):
                return f"ACK>{self.gps_coordinates['helipad']}"
            else:
                return "NACK: No GPS data available"
        elif command == ZMQTopics.TANK_GPS.name:
            if hasattr(self, "gps_coordinates"):
                return f'ACK>{self.gps_coordinates["tank" if IS_SIMULATION else "real_tank"]}'
            else:
                return "NACK: No GPS data available"

        else:
            logger.error(f"Unknown command: {command}")
            return "NACK: Unknown command"

    def control_receiver_loop(self):
        """Control command receiving loop - runs in a separate thread"""
        logger.info("Control receiver started")

        while self.running:
            try:
                # Non-blocking receive with timeout to allow checking running flag
                if self.control_socket.poll(timeout=100) != 0:  # 100ms timeout
                    message = self.control_socket.recv_string()
                    response = self.handle_command(message)
                    self.control_socket.send_string(response)
                    logger.info(f"Received command: {message}, Response: {response}")
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error in control receiver: {e}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in control receiver: {e}")
                time.sleep(0.1)

    def start(self):
        if self.running:
            logger.warning("Server is already running")
            return

        self.running = True

        # Start video publisher thread
        self.video_thread = threading.Thread(target=self.video_publisher_loop)
        self.video_thread.daemon = True
        self.video_thread.start()

        # Start control receiver thread
        self.control_thread = threading.Thread(target=self.control_receiver_loop)
        self.control_thread.daemon = True
        self.control_thread.start()

        logger.info("Server started")

    def stop(self):
        """Stop the server"""
        logger.info("Stopping server...")
        self.running = False

        if self.video_thread:
            self.video_thread.join(timeout=2.0)

        if self.control_thread:
            self.control_thread.join(timeout=2.0)

        # Clean up ZMQ resources
        self.video_socket.close()
        self.control_socket.close()
        self.context.term()

        logger.info("Server stopped")


def main():

    # Convert video_source to int if it's a number
    try:
        args.video_source = int(args.video_source)
    except ValueError:
        pass  # Keep as string if it's not a number (e.g., file path)

    server = ZMQServer(
        is_simulation=args.is_simulation,
        video_port=args.video_port,
        control_port=args.control_port,
        video_source=args.video_source,
    )
    # Start the client acceptance thread
    accept_thread = threading.Thread(target=accept_clients, daemon=True)

    # Start the serial-to-TCP forwarding thread
    forward_thread = threading.Thread(target=forward_from_serial_to_tcp, daemon=True)

    try:
        accept_thread.start()
        forward_thread.start()
        server.start()
        logger.info("Server running. Press Ctrl+C to stop.")

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        server.stop()
        # Clean up
        tcp_server.close()
        connection.close()
        with clients_lock:
            for client in clients:
                try:
                    client.close()
                except:
                    pass


if __name__ == "__main__":
    main()
