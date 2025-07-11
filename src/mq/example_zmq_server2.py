#!/usr/bin/env python3
import argparse
import logging
import queue
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import zmq
from pymavlink import mavutil

from src.controls.detection import yolo  # Assuming this is your YOLO module
from src.controls.mavlink import gz
from src.mq.messages import ZMQTopics

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zmq-video-server")

# Configuration
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 57600
TCP_HOST = "0.0.0.0"
TCP_PORT = 16550
SIMULATION_UDP_PORT = "udp:127.0.0.1:14550"
MAX_CLIENTS = 10

# YOLO Configuration
GIMBAL_FOV_DEG = 60
HELIPAD_CLASS = "helipad"
DETECTION_THRESHOLD = 0.5


class MAVLinkBridge:
    """Handles MAVLink connection and TCP forwarding"""

    def __init__(self, is_simulation: bool):
        self.is_simulation = is_simulation
        self.connection = None
        self.tcp_server = None
        self.clients = set()
        self.clients_lock = threading.Lock()
        self.running = False
        self.executor = ThreadPoolExecutor(
            max_workers=MAX_CLIENTS, thread_name_prefix="client"
        )

    def setup_connection(self) -> bool:
        """Setup MAVLink connection"""
        try:
            if self.is_simulation:
                logger.info("Connecting to simulation via UDP...")
                self.connection = mavutil.mavlink_connection(
                    SIMULATION_UDP_PORT, source_system=255
                )
            else:
                logger.info(f"Connecting to serial port {SERIAL_PORT}...")
                self.connection = mavutil.mavlink_connection(
                    SERIAL_PORT, baud=BAUD_RATE, source_system=255
                )
            logger.info("MAVLink connection established")
            return True
        except Exception as e:
            logger.error(f"Error connecting to MAVLink: {e}")
            return False

    def setup_tcp_server(self) -> bool:
        """Setup TCP server for MAVLink forwarding"""
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind((TCP_HOST, TCP_PORT))
            self.tcp_server.listen(MAX_CLIENTS)
            logger.info(f"TCP server listening on {TCP_HOST}:{TCP_PORT}")
            return True
        except Exception as e:
            logger.error(f"Error setting up TCP server: {e}")
            return False

    def handle_client(self, client_socket, client_address):
        """Handle individual TCP client"""
        logger.info(f"New client connected: {client_address}")

        try:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    if self.connection:
                        self.connection.write(data)

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error reading from client {client_address}: {e}")
                    break
        finally:
            with self.clients_lock:
                self.clients.discard(client_socket)
            try:
                client_socket.close()
            except:
                pass
            logger.info(f"Client disconnected: {client_address}")

    def accept_clients(self):
        """Accept new TCP clients using thread pool"""
        while self.running:
            try:
                if self.tcp_server:
                    client_socket, client_address = self.tcp_server.accept()

                    with self.clients_lock:
                        if len(self.clients) >= MAX_CLIENTS:
                            logger.warning(
                                "Maximum clients reached, rejecting connection"
                            )
                            client_socket.close()
                            continue

                        self.clients.add(client_socket)
                        client_socket.settimeout(1.0)  # Set timeout for recv

                    # Submit client handling to thread pool
                    self.executor.submit(
                        self.handle_client, client_socket, client_address
                    )

            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting client: {e}")
                    time.sleep(1)

    def forward_to_clients(self):
        """Forward MAVLink messages to TCP clients"""
        while self.running:
            try:
                if self.connection:
                    msg = self.connection.recv_match(blocking=False, timeout=0.1)
                    if msg is not None:
                        msg_bytes = msg.get_msgbuf()

                        with self.clients_lock:
                            disconnected = []
                            for client in self.clients.copy():
                                try:
                                    client.send(msg_bytes)
                                except:
                                    disconnected.append(client)

                            # Remove disconnected clients
                            for client in disconnected:
                                self.clients.discard(client)
                                try:
                                    client.close()
                                except:
                                    pass
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error forwarding to clients: {e}")
                time.sleep(0.1)

    def get_drone_state(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Get current drone GPS and attitude"""
        if not self.connection:
            return None, None

        try:
            gps = attitude = None

            # Non-blocking message reads
            gps_msg = self.connection.recv_match(
                type="GLOBAL_POSITION_INT", blocking=False
            )
            if gps_msg:
                gps = {
                    "lat": gps_msg.lat / 1e7,
                    "lon": gps_msg.lon / 1e7,
                    "alt": gps_msg.alt / 1000.0,
                }

            attitude_msg = self.connection.recv_match(type="ATTITUDE", blocking=False)
            if attitude_msg:
                attitude = {
                    "roll": attitude_msg.roll,
                    "pitch": attitude_msg.pitch,
                    "yaw": attitude_msg.yaw,
                }

            return gps, attitude
        except Exception as e:
            logger.error(f"Error getting drone state: {e}")
            return None, None

    def start(self):
        """Start the MAVLink bridge"""
        if not self.setup_connection() or not self.setup_tcp_server():
            return False

        self.running = True

        # Start accept thread
        self.accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        self.accept_thread.start()

        # Start forward thread
        self.forward_thread = threading.Thread(
            target=self.forward_to_clients, daemon=True
        )
        self.forward_thread.start()

        logger.info("MAVLink bridge started")
        return True

    def stop(self):
        """Stop the MAVLink bridge"""
        logger.info("Stopping MAVLink bridge...")
        self.running = False

        # Close all client connections
        with self.clients_lock:
            for client in self.clients.copy():
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        # Close servers
        if self.tcp_server:
            self.tcp_server.close()
        if self.connection:
            self.connection.close()

        logger.info("MAVLink bridge stopped")


class ZMQServer:
    """Main ZMQ server with video streaming and control"""

    def __init__(
        self,
        video_port: int = 5555,
        control_port: int = 5556,
        video_source: int = 0,
        is_simulation: bool = False,
        weights_path: str = "src/controls/detection/best.pt",
    ):
        self.is_simulation = is_simulation
        self.context = zmq.Context()

        # ZMQ sockets
        self.video_socket = self.context.socket(zmq.PUB)
        self.video_socket.bind(f"tcp://*:{video_port}")

        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(f"tcp://*:{control_port}")

        # Video capture
        self.cap = None
        self.video_source = video_source
        self.frame_width = 640
        self.frame_height = 480

        # YOLO estimator
        self.estimator = None
        self.weights_path = weights_path

        # State
        self.hook_state = "dropped"
        self.detected_helipad_coords = None
        self.running = False

        # MAVLink bridge
        self.mavlink_bridge = MAVLinkBridge(is_simulation)

        # Single thread for video processing
        self.video_thread = None
        self.control_thread = None

        # Setup simulation if needed
        if self.is_simulation:
            self._setup_simulation()

        logger.info(
            f"ZMQ Server initialized - Video: {video_port}, Control: {control_port}"
        )

    def _setup_simulation(self):
        """Setup Gazebo simulation streaming"""
        logger.info("Setting up simulation video streaming...")
        try:
            success = gz.enable_streaming(
                world="delivery_runway",
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
            )
            if not success:
                logger.error("Failed to enable simulation streaming")
        except Exception as e:
            logger.error(f"Error setting up simulation: {e}")

    def _initialize_yolo(self) -> bool:
        """Initialize YOLO estimator"""
        try:
            self.estimator = yolo.YoloObjectTracker(
                model_path=self.weights_path,
                hfov_rad=GIMBAL_FOV_DEG,
                frame_height=self.frame_height,
                frame_width=self.frame_width,
                log=logger,
            )
            logger.info("YOLO estimator initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YOLO: {e}")
            return False

    def _start_capture(self) -> bool:
        """Start video capture"""
        try:
            if self.is_simulation:
                self.cap = gz.GazeboVideoCapture()
            else:
                self.cap = cv2.VideoCapture(self.video_source)

            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.video_source}")
                return False

            # Get frame dimensions
            if hasattr(self.cap, "get"):
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            logger.info(
                f"Video capture started: {self.frame_width}x{self.frame_height}"
            )
            return True
        except Exception as e:
            logger.error(f"Error starting video capture: {e}")
            return False

    def _encode_frame(
        self, frame: np.ndarray, frame_type: str = "raw"
    ) -> Tuple[bytes, bytes]:
        """Encode frame to JPEG"""
        topic = b"video" if frame_type == "raw" else b"processed_video"
        _, jpeg_frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return topic, jpeg_frame.tobytes()

    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[Dict]]:
        """Process frame with YOLO detection"""
        if not self.estimator:
            return frame, None

        try:
            # Get current drone state
            gps, attitude = self.mavlink_bridge.get_drone_state()
            if not gps or not attitude:
                return frame, None

            # Process with YOLO
            (
                annotated_frame,
                detected_coords,
                center_pose,
            ) = self.estimator.process_frame(
                frame=frame,
                drone_gps=gps,
                drone_attitude=attitude,
                object_class=HELIPAD_CLASS,
                threshold=DETECTION_THRESHOLD,
            )

            # Store detected coordinates
            if detected_coords:
                self.detected_helipad_coords = detected_coords
                logger.debug(f"Helipad detected: {detected_coords}")

            return annotated_frame, detected_coords
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return frame, None

    def _video_loop(self):
        """Main video processing loop"""
        if not self._start_capture():
            logger.error("Failed to start video capture")
            return

        # Initialize YOLO
        yolo_available = self._initialize_yolo()
        if not yolo_available:
            logger.warning("YOLO not available - object detection disabled")

        logger.info("Video processing started")
        fps_count = 0
        fps_timer = time.time()

        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue

                # Send raw frame
                topic, encoded_frame = self._encode_frame(frame, "raw")
                self.video_socket.send_multipart([topic, encoded_frame])

                # Process and send annotated frame
                if yolo_available:
                    processed_frame, _ = self._process_frame(frame)
                else:
                    processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                topic, processed_encoded = self._encode_frame(
                    processed_frame, "processed"
                )
                self.video_socket.send_multipart([topic, processed_encoded])

                # FPS tracking
                fps_count += 1
                if time.time() - fps_timer > 5:
                    logger.info(f"Video FPS: {fps_count / 5:.1f}")
                    fps_count = 0
                    fps_timer = time.time()

                time.sleep(0.01)  # ~100 FPS max

            except Exception as e:
                logger.error(f"Error in video loop: {e}")
                time.sleep(0.1)

        # Cleanup
        if self.cap:
            self.cap.release()
        logger.info("Video processing stopped")

    def _control_loop(self):
        """Control command handling loop"""
        logger.info("Control loop started")

        while self.running:
            try:
                if self.control_socket.poll(timeout=100):
                    message = self.control_socket.recv_string()
                    response = self._handle_command(message)
                    self.control_socket.send_string(response)
                    logger.info(f"Command: {message} -> {response}")
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in control loop: {e}")
                time.sleep(0.1)

        logger.info("Control loop stopped")

    def _handle_command(self, command: str) -> str:
        """Handle control commands"""
        command = command.strip()

        if command == ZMQTopics.DROP_LOAD.name:
            return "ACK: Load dropped"
        elif command == ZMQTopics.PICK_LOAD.name:
            return "ACK: Load picked"
        elif command == ZMQTopics.RAISE_HOOK.name:
            if self.hook_state == "raised":
                return "ACK: Hook already raised"
            self.hook_state = "raised"
            return "ACK: Hook raised"
        elif command == ZMQTopics.DROP_HOOK.name:
            if self.hook_state == "dropped":
                return "ACK: Hook already dropped"
            self.hook_state = "dropped"
            return "ACK: Hook dropped"
        elif command == ZMQTopics.STATUS.name:
            return f"ACK: Hook is {self.hook_state}"
        elif command.startswith("mission_guided_landing"):
            return self._handle_guided_landing(command)
        else:
            return "NACK: Unknown command"

    def _handle_guided_landing(self, command: str) -> str:
        """Handle guided landing command"""
        try:
            parts = command.split()
            if len(parts) < 4:
                return "NACK: Invalid format. Use: mission_guided_landing lat lon alt"

            curr_lat = float(parts[1])
            curr_lon = float(parts[2])
            curr_alt = float(parts[3])

            if self.detected_helipad_coords:
                coords = self.detected_helipad_coords
                helipad_lat = coords.get("lat", curr_lat)
                helipad_lon = coords.get("lon", curr_lon)
                helipad_alt = coords.get("alt", curr_alt)

                return f"ACK: Helipad coordinates {helipad_lat},{helipad_lon},{helipad_alt}"
            else:
                return "NACK: No helipad detected"

        except (ValueError, IndexError) as e:
            return f"NACK: Error parsing coordinates: {e}"

    def start(self) -> bool:
        """Start the ZMQ server"""
        if self.running:
            logger.warning("Server already running")
            return False

        # Start MAVLink bridge
        if not self.mavlink_bridge.start():
            logger.error("Failed to start MAVLink bridge")
            return False

        self.running = True

        # Start video thread
        self.video_thread = threading.Thread(target=self._video_loop, daemon=True)
        self.video_thread.start()

        # Start control thread
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()

        logger.info("ZMQ Server started")
        return True

    def stop(self):
        """Stop the ZMQ server"""
        logger.info("Stopping ZMQ server...")
        self.running = False

        # Wait for threads to finish
        if self.video_thread:
            self.video_thread.join(timeout=2.0)
        if self.control_thread:
            self.control_thread.join(timeout=2.0)

        # Stop MAVLink bridge
        self.mavlink_bridge.stop()

        # Close ZMQ sockets
        self.video_socket.close()
        self.control_socket.close()
        self.context.term()

        logger.info("ZMQ Server stopped")


def main():
    parser = argparse.ArgumentParser(description="ZMQ Drone Server")
    parser.add_argument("--is-simulation", action="store_true", help="Simulation mode")
    parser.add_argument("--video-port", type=int, default=5555, help="Video port")
    parser.add_argument("--control-port", type=int, default=5556, help="Control port")
    parser.add_argument("--video-source", default=0, help="Video source")
    parser.add_argument(
        "--weights-path", default="yolo_weights.pt", help="YOLO weights"
    )

    args = parser.parse_args()

    # Convert video source to int if possible
    try:
        args.video_source = int(args.video_source)
    except ValueError:
        pass

    # Create and start server
    server = ZMQServer(
        video_port=args.video_port,
        control_port=args.control_port,
        video_source=args.video_source,
        is_simulation=args.is_simulation,
        weights_path=args.weights_path,
    )

    try:
        if server.start():
            logger.info("Server running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        else:
            logger.error("Failed to start server")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
