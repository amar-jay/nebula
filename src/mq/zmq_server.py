#!/usr/bin/env python3
import argparse
import asyncio
import logging
import queue
import socket
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import zmq
import zmq.asyncio

from src.controls.detection import yolo
from src.controls.mavlink import ardupilot, gz, mission_types
from src.mq.crane import CraneControls, ExampleController, ZMQTopics

IMAGE_QUALITY = 50  # JPEG quality for video frames
CPU_BURNOUT = 0.03  # CPU burn rate for async tasks, adjust as needed


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Explicit console handler
)
logger = logging.getLogger("zmq-server")
logger.setLevel(logging.DEBUG)  # Ensure logger level is set


@dataclass
class FrameData:
    """Data structure for frame processing"""

    mode: str  # default is "UNKNOWN"
    frame: np.ndarray
    timestamp: float
    drone_position: Tuple[float, float, float]
    drone_attitude: Any
    ground_level: float


@dataclass
class ProcessedResult:
    """Result of frame processing"""

    processed_frame: np.ndarray
    gps_coordinates: Dict[str, Tuple[float, float]]
    pixel_coordinates: Dict[str, Tuple[int, int]]
    timestamp: float


class AsyncVideoCapture:
    """Asynchronous video capture that runs in a separate thread"""

    def __init__(self, video_source):
        self.video_source = video_source
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=2)  # Only keep 1-2 latest frames
        self.running = False
        self.capture_thread = None
        self.fps_stats = {"frame_count": 0, "last_time": time.time()}

    def start(self) -> bool:
        """Start video capture thread"""
        try:
            self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source {self.video_source}")
                return False

            # Set buffer size to minimize latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.running = True
            self.capture_thread = threading.Thread(
                target=self._capture_loop, daemon=True
            )
            self.capture_thread.start()

            logger.info("Video capture thread started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting video capture: {e}")
            return False

    def stop(self):
        """Stop video capture thread"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info("Video capture stopped")

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame, non-blocking. Returns None if no frame available."""
        try:
            # Get the most recent frame, discard older ones
            latest_frame = None
            frames_discarded = 0
            while not self.frame_queue.empty():
                try:
                    latest_frame = self.frame_queue.get_nowait()
                    frames_discarded += 1
                except queue.Empty:
                    break

            # Log if we're discarding too many frames (indicates capture is faster than consumption)
            if frames_discarded > 1:
                logger.debug(
                    f"Discarded {frames_discarded - 1} old frames, using latest"
                )

            return latest_frame
        except Exception as e:
            logger.warning(f"Error getting latest frame: {e}")
            return None

    def is_running(self) -> bool:
        """Check if video capture is running"""
        return self.running and self.capture_thread and self.capture_thread.is_alive()

    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to capture frame from video source")
                    time.sleep(0.1)
                    continue

                # Update FPS stats
                self.fps_stats["frame_count"] += 1
                current_time = time.time()
                if current_time - self.fps_stats["last_time"] > 5:
                    fps = self.fps_stats["frame_count"] / 5
                    logger.debug(f"Capturing video at {fps:.1f} FPS")
                    self.fps_stats["frame_count"] = 0
                    self.fps_stats["last_time"] = current_time

                # Add frame to queue, drop oldest if full
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        continue

                # Small sleep to prevent excessive CPU usage
                time.sleep(0.001)  # ~1000 FPS max capture rate

            except Exception as e:
                logger.error(f"Error in video capture loop: {e}")
                time.sleep(0.1)


class AsyncFrameProcessor:
    """Asynchronous frame processor that doesn't block the main video loop"""

    def __init__(self, tracker: yolo.YoloObjectTracker, object_classes, max_workers=2):
        self.tracker = tracker
        self.object_classes = object_classes
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_queue = queue.Queue(
            maxsize=3
        )  # Small buffer to prevent memory issues
        self.results_queue = queue.Queue(maxsize=10)
        self.running = False
        self.worker_thread = None

    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        self.executor.shutdown(wait=True)

    def submit_frame(self, frame_data: FrameData) -> bool:
        """Submit a frame for processing. Returns False if queue is full."""
        try:
            self.processing_queue.put_nowait(frame_data)
            return True
        except queue.Full:
            logger.warning("Processing queue is full, dropping oldest frame")
            return False

    def get_result(self) -> Optional[ProcessedResult]:
        """Get the latest processed result, non-blocking."""
        try:
            return self.results_queue.get_nowait()
        except queue.Empty:
            return None

    def _worker_loop(self):
        """Worker thread that processes frames asynchronously"""
        while self.running:
            try:
                # Get frame data with timeout
                frame_data = self.processing_queue.get(timeout=0.1)

                # Process in thread pool to avoid blocking
                future = self.executor.submit(self._process_frame, frame_data)

                # Wait for result with timeout
                try:
                    result = future.result(timeout=0.5)  # 500ms timeout for processing

                    # Put result in results queue, drop oldest if full
                    try:
                        self.results_queue.put_nowait(result)
                    except queue.Full:
                        # Drop oldest result
                        try:
                            self.results_queue.get_nowait()
                            self.results_queue.put_nowait(result)
                        except queue.Empty:
                            continue

                except Exception as e:
                    logger.warning("Frame processing failed: %s", e)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Error in frame processor worker: %s", e)
                time.sleep(0.1)

    def _process_frame(self, frame_data: FrameData) -> ProcessedResult:
        """Process a single frame"""
        processed_frame, gps_coords, pixel_coords = self.tracker.process_frame(
            frame=frame_data.frame,
            drone_gps=frame_data.drone_position,
            drone_attitude=frame_data.drone_attitude,
            ground_level_masl=frame_data.ground_level,
            object_classes=self.object_classes,
        )

        try:
            processed_frame = self.tracker.write_on_frame(
                frame=processed_frame,
                curr_gps=frame_data.drone_position,
                gps_coords=gps_coords,
                pixel_coords=pixel_coords,
                mode=frame_data.mode,
                object_classes=self.object_classes,
            )
        except Exception:
            logger.error(
                "Error writing on frame in _process_frame: %s", traceback.format_exc()
            )
            processed_frame = frame_data.frame.copy()

        return ProcessedResult(
            processed_frame=processed_frame,
            gps_coordinates=gps_coords,
            pixel_coordinates=pixel_coords,
            timestamp=frame_data.timestamp,
        )


class MAVLinkProxy:
    """Handles MAVLink connection and TCP proxy in a clean way"""

    def __init__(
        self, connection_string: str, tcp_host: str = "0.0.0.0", tcp_port: int = 16550
    ):
        self.connection_string = connection_string
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.connection = None
        self.tcp_server = None
        self.clients: list[socket.socket] = []
        self.clients_lock = threading.Lock()
        self.running = False
        self.drone_data = dict()

    def start(self):
        # Initialize MAVLink connection
        try:
            self.connection = ardupilot.ArdupilotConnection(
                connection_string=self.connection_string
            )
            logger.info("MAVLink connection established")
        except ConnectionError:
            logger.error("Failed to connect to MAVLink at %s", self.connection_string)
            raise

        # Set up TCP server
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind((self.tcp_host, self.tcp_port))
        self.tcp_server.listen(5)
        logger.info("TCP server listening on %s:%d", self.tcp_host, self.tcp_port)

        self.running = True

        # Start background threads
        threading.Thread(target=self._accept_clients, daemon=True).start()
        threading.Thread(target=self._forward_serial_to_tcp, daemon=True).start()

    def stop(self):
        self.running = False
        if self.tcp_server:
            self.tcp_server.close()
        if self.connection:
            self.connection.close()
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception:
                    logger.warning("Failed to close client socket")
            self.clients.clear()

    def get_drone_data(self) -> Any | None:
        if (
            "drone_position" not in self.drone_data
            or not self.drone_data["drone_position"]
        ):
            logger.warning("Drone position not available")
            return None
        if (
            "drone_attitude" not in self.drone_data
            or not self.drone_data["drone_attitude"]
        ):
            logger.warning("Drone attitude not available")
            return None
        if "ground_level" not in self.drone_data or not self.drone_data["ground_level"]:
            logger.warning("Ground level not available")
            return None
        return (
            self.drone_data["drone_position"],
            self.drone_data["drone_attitude"],
            self.drone_data["ground_level"],
            self.drone_data.get("mode", "UNKNOWN"),
        )

    def fetch_drone_data(self, msg):
        """Get current drone position, attitude, and ground level"""
        if not self.connection:
            logger.warning("MAVLink connection not established")
            return

        msg_type = msg.get_type()

        if msg_type == "GLOBAL_POSITION_INT":
            # Convert values to standard units
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            relative_alt = msg.relative_alt / 1000.0  # meters
            alt_amsl = msg.alt / 1000.0  # meters

            self.drone_data["drone_position"] = (lat, lon, alt_amsl)
            self.drone_data["ground_level"] = alt_amsl - relative_alt

        elif msg_type == "ATTITUDE":
            roll = msg.roll
            pitch = msg.pitch
            yaw = msg.yaw

            # Normalize yaw to [0, 2π]
            if yaw < 0:
                yaw += 2 * np.pi

            self.drone_data["drone_attitude"] = (roll, pitch, yaw)

        self.drone_data["mode"] = self.connection.get_mode()

    def _accept_clients(self):
        while self.running:
            try:
                client_socket, client_address = self.tcp_server.accept()
                with self.clients_lock:
                    self.clients.append(client_socket)
                logger.info("New client connected: %s", client_address)

                # Handle client in separate thread
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                ).start()
            except Exception as e:
                if self.running:
                    logger.error("Error accepting client: %s", e)
                    time.sleep(1)

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    if self.connection:
                        self.connection.master.write(data)
                except Exception as e:
                    logger.error(f"Error handling client {client_address}: {e}")
                    break
        finally:
            with self.clients_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            client_socket.close()
            logger.info(f"Client disconnected: {client_address}")

    def _forward_serial_to_tcp(self):
        while self.running:
            try:
                if not self.connection:
                    time.sleep(0.1)
                    continue

                msg = self.connection.master.recv_match(blocking=False)
                if msg is not None:
                    # Fetch drone data for gps estimation
                    self.fetch_drone_data(msg)

                    msg_bytes = msg.get_msgbuf()

                    with self.clients_lock:
                        disconnected_clients: list[socket.socket] = []
                        for client in self.clients:
                            try:
                                client.send(msg_bytes)
                            except Exception:
                                disconnected_clients.append(client)

                        for client in disconnected_clients:
                            self.clients.remove(client)
                            try:
                                client.close()
                            except:
                                pass
                else:
                    time.sleep(0.001)  # Small sleep when no messages

            except Exception as e:
                logger.error(f"Error in serial to TCP forwarding: {e}")
                time.sleep(0.1)


class ZMQServer:
    """ZMQ server that publishes video and handles control commands"""

    def __init__(
        self,
        video_output: str,
        control_address: int = 5556,
        video_source: int = 0,
        is_simulation: bool = False,
    ):
        self.video_output = video_output
        self.control_address = control_address
        self.video_source = video_source
        self.is_simulation = is_simulation
        if is_simulation:
            self.crane_controls = ExampleController()
        else:
            self.crane_controls = CraneControls()

        # ZMQ Context
        self.context = zmq.asyncio.Context()

        # Sockets
        self.video_socket = None
        self.control_socket = None
        self.crane_controls = None

        # Video capture
        self.video_capture = None

        # State
        self.hook_state = "dropped"
        self.running = False

        # Latest processed results
        self.latest_gps_coordinates = {}
        self.latest_pixel_coordinates = {}

        # Frame processor
        self.frame_processor = None

        # Object classes
        self.object_classes = ["helipad", "tank" if is_simulation else "real_tank"]

        if is_simulation:
            camera_intrinsics = gz.get_camera_params(
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
                world="delivery_runway",
            )
        else:
            camera_intrinsics = mission_types.get_camera_params()

        if camera_intrinsics is None:
            raise RuntimeError("Failed to get camera parameters")

        camera_intrinsics = camera_intrinsics.get("camera_intrinsics", None)
        if camera_intrinsics is None:
            raise RuntimeError("Camera intrinsics not found")

        self.tracker = yolo.YoloObjectTracker(
            K=camera_intrinsics,
            model_path="src/controls/detection/sim.pt"
            if is_simulation
            else "src/controls/detection/main.pt",
        )

        # Initialize frame processor
        self.frame_processor = AsyncFrameProcessor(
            tracker=self.tracker, object_classes=self.object_classes, max_workers=2
        )

        # Initialize video capture
        self.video_capture = AsyncVideoCapture(video_source=self.video_source)

    def _encode_frame(
        self, frame: np.ndarray, topic_prefix: str = ""
    ) -> Tuple[bytes, bytes]:  # TODO: use a more efficient implementation in the future
        """Encode frame to JPEG"""
        topic = f"{topic_prefix}video".encode()
        encode_params = [
            cv2.IMWRITE_JPEG_QUALITY,
            IMAGE_QUALITY,
            cv2.IMWRITE_JPEG_OPTIMIZE,
            1,
        ]

        _, jpeg_frame = cv2.imencode(".jpg", frame, encode_params)
        return topic, jpeg_frame.tobytes()

    async def _video_publisher_loop(self, mavlink_proxy: MAVLinkProxy):
        """Main video publishing loop"""
        logger.info("Video publishing loop started")

        frame_count = 0
        fps_timer = time.time()
        last_frame_time = time.time()

        while self.running:
            try:
                # Get the latest frame from the threaded capture
                frame = self.video_capture.get_latest_frame()
                if frame is None:
                    # Check if video capture is still healthy
                    if not self.video_capture.is_running():
                        logger.error(
                            "Video capture thread has died, attempting restart..."
                        )
                        if not self.video_capture.start():
                            logger.error("Failed to restart video capture")
                            await asyncio.sleep(1.0)
                            continue

                    # No new frame available, wait briefly
                    await asyncio.sleep(0.01)
                    continue

                # Track frame timing
                current_time = time.time()
                frame_interval = current_time - last_frame_time
                last_frame_time = current_time

                # Always send raw frame
                topic, encoded_frame = self._encode_frame(frame)
                await self.video_socket.send_multipart(
                    [topic, encoded_frame], zmq.NOBLOCK
                )

                # Submit frame for processing (non-blocking)
                data = mavlink_proxy.get_drone_data()
                if data is None:
                    logger.debug("Drone data not available, skipping frame processing")
                    await asyncio.sleep(0.03)
                    continue

                (
                    drone_pos,
                    drone_att,
                    ground_level,
                    mode,
                ) = data

                frame_data = FrameData(
                    frame=frame.copy(),
                    timestamp=current_time,
                    drone_position=drone_pos,
                    drone_attitude=drone_att,
                    ground_level=ground_level,
                    mode=mode,
                )

                # Submit for processing (non-blocking)
                if not self.frame_processor.submit_frame(frame_data):
                    logger.debug(
                        "Frame processor queue full, skipping frame processing"
                    )

                # Check for processed results
                result = self.frame_processor.get_result()
                if result:
                    # Update latest coordinates
                    if result.gps_coordinates is not None:
                        self.latest_gps_coordinates = result.gps_coordinates
                    if result.pixel_coordinates is not None:
                        self.latest_pixel_coordinates = result.pixel_coordinates

                    # Send processed frame
                    topic, processed_frame = self._encode_frame(
                        result.processed_frame, "processed_"
                    )
                    await self.video_socket.send_multipart(
                        [topic, processed_frame], zmq.NOBLOCK
                    )
                else:
                    logger.debug("No processed result available")

                frame_count += 1

                # FPS logging
                if current_time - fps_timer > 5:
                    fps = frame_count / 5
                    avg_interval = 5 / frame_count if frame_count > 0 else 0
                    logger.debug(
                        f"Publishing video at {fps:.1f} FPS (avg interval: {avg_interval * 1000:.1f}ms)"
                    )
                    frame_count = 0
                    fps_timer = current_time

                # Small sleep to prevent CPU overload
                await asyncio.sleep(CPU_BURNOUT)

            except Exception:
                logger.error("Error in video loop:\n%s", traceback.format_exc())
                await asyncio.sleep(0.1)

        logger.info("Video publishing loop stopped")

    async def _control_receiver_loop(self):
        """Control command receiver loop"""
        logger.info("Control receiver started")

        while self.running:
            try:
                # Check for messages with timeout
                if await self.control_socket.poll(timeout=100):
                    message = await self.control_socket.recv_string()
                    response = self._handle_command(message)
                    await self.control_socket.send_string(response)
                    if "NACK" not in message:
                        logger.info(f"Command: {message} -> Response: {response}")

            except Exception as e:
                logger.error(f"Error in control receiver: {e}")
                await asyncio.sleep(0.1)

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
            if self.latest_gps_coordinates and "helipad" in self.latest_gps_coordinates:
                coords = self.latest_gps_coordinates["helipad"]
                return f"ACK>{coords[0]},{coords[1]}"
            else:
                return "NACK: No GPS data available"
        elif command == ZMQTopics.TANK_GPS.name:
            tank_key = "tank" if self.is_simulation else "real_tank"
            if self.latest_gps_coordinates and tank_key in self.latest_gps_coordinates:
                coords = self.latest_gps_coordinates[tank_key]
                return f"ACK>{coords[0]},{coords[1]}"
            else:
                return "NACK: No GPS data available"
        else:
            logger.error("Unknown command: %s", command)
            return "NACK: Unknown command"

    async def start(self, mavlink_proxy: MAVLinkProxy):
        """Start the server"""
        if self.running:
            logger.warning("Server is already running")
            return

        # Initialize ZMQ sockets
        self.video_socket = self.context.socket(zmq.PUB)
        self.video_socket.bind(self.video_output)

        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(self.control_address)

        # Start video capture first
        if not self.video_capture.start():
            logger.error("Failed to start video capture")
            raise RuntimeError("Video capture initialization failed")

        # Start frame processor
        self.frame_processor.start()

        self.running = True
        logger.info("Server started - video capture and frame processing active")

        # Run both loops concurrently
        await asyncio.gather(
            self._video_publisher_loop(mavlink_proxy), self._control_receiver_loop()
        )

    def stop(self):
        """Stop the server"""
        logger.info("Stopping server...")
        self.running = False

        # Stop video capture
        if self.video_capture:
            self.video_capture.stop()

        # Stop frame processor
        if self.frame_processor:
            self.frame_processor.stop()

        # Close sockets
        if self.video_socket:
            self.video_socket.close()
        if self.control_socket:
            self.control_socket.close()

        # Terminate context
        self.context.term()

        logger.info("Server stopped")


async def main():
    parser = argparse.ArgumentParser(description="ZMQ Video Server")
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

    # Convert video_source to int if it's a number
    try:
        args.video_source = int(args.video_source)
    except ValueError:
        pass

    gz_config = mission_types.get_gazebo_config()

    config = mission_types.get_config()
    # Initialize MAVLink proxy
    # connection_string = "udp:127.0.0.1:14550" if args.is_simulation else "/dev/ttyUSB0"
    mavlink_proxy = MAVLinkProxy(config.mavproxy_source)

    # Enable video streaming for simulation
    if args.is_simulation:
        logger.info("Enabling video streaming for simulation")
        done = gz.enable_streaming(
            world=gz_config.world,
            model_name=gz_config.model_name,
            camera_link=gz_config.camera_link,
        )
        if not done:
            logger.error("Failed to enable streaming")
            return

    # Initialize server
    server = ZMQServer(
        video_output=config.video_output,
        control_address=config.control_address,
        video_source=config.video_source,
        is_simulation=args.is_simulation,
    )

    try:
        # Start MAVLink proxy
        mavlink_proxy.start()

        # Start server
        logger.info("Starting server. Press Ctrl+C to stop.")
        await server.start(mavlink_proxy)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error running server: {e}")
    finally:
        # Cleanup
        server.stop()
        mavlink_proxy.stop()


if __name__ == "__main__":
    asyncio.run(main())
