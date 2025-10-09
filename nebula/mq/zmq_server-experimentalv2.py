"""
The on-drone ZMQ server that publishes video, proxies MAVLink, and handles control commands.
It uses asynchronous frame processing to avoid blocking the main video loop.
It can run in simulation mode with Gazebo or with a real drone.


This is an experimental version 2 of the ZMQ server without a thread pool for frame processing.
It uses asyncio's run_in_executor to offload frame processing to a thread pool, which simplifies the code and avoids managing a separate thread pool.
However, it may have different performance characteristics and a couple of bugs or bottlenecks. It should be tested thoroughly.
"""

#!/usr/bin/env python3
import argparse
import asyncio
import logging
import os
import socket
import threading
import time
import traceback
from typing import Any, Dict, NamedTuple, Optional, Tuple

import cv2
import numpy as np
import zmq
import zmq.asyncio

from nebula.controls.detection import yolo
from nebula.controls.mavlink import ardupilot, gz, mission_types
from nebula.mq.crane import CraneControls
from nebula.mq.logger import init_logging
from nebula.mq.messages import ZMQTopics

IMAGE_QUALITY = 50  # JPEG quality for video frames
CPU_BURNOUT = 0.03  # CPU burn rate for async tasks, adjust as needed


# Configure logging
logger = init_logging(
    level=logging.INFO,
    log_file=os.path.join(os.path.expanduser("~"), "nebula-zmq-server.log"),
)


class FrameData(NamedTuple):
    """Data structure for frame processing"""

    mode: str  # default is "UNKNOWN"
    frame: np.ndarray
    timestamp: float
    drone_position: Tuple[float, float, float]
    drone_attitude: Any
    ground_level: float


class ProcessedResult(NamedTuple):
    """Result of frame processing"""

    processed_frame: np.ndarray
    gps_coordinates: Dict[str, Tuple[float, float]]
    pixel_coordinates: Dict[str, Tuple[int, int]]
    timestamp: float


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
                    logger.error("Error handling client %s: %s", client_address, e)
                    break
        finally:
            with self.clients_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            client_socket.close()
            logger.info("Client disconnected: %s", client_address)

    def _forward_serial_to_tcp(self):
        while self.running:
            try:
                if not self.connection:
                    time.sleep(0.1)
                    continue

                msg = self.connection.master.recv_match(blocking=False)
                if msg is not None:
                    # Filter drone data for GPS estimation
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
                            except Exception:
                                pass
                else:
                    time.sleep(0.001)  # Small sleep when no messages

            except Exception as e:
                logger.error("Error in serial to TCP forwarding: %s", e)
                time.sleep(0.1)


class ZMQServer:
    """ZMQ server that publishes video and handles control commands"""

    def __init__(
        self,
        video_port: int = 5555,
        control_port: int = 5556,
        crane_controller_address: Tuple[str, int] = ("/dev/ttyUSB1", 57600),
        video_source: int = 0,
        is_simulation: bool = False,
    ):
        self.video_port = video_port
        self.control_port = control_port
        self.video_source = video_source
        self.is_simulation = is_simulation

        # ZMQ Context
        self.context = zmq.asyncio.Context()

        # Sockets
        self.video_socket = None
        self.control_socket = None

        # Video capture
        self.cap = None

        # State
        self.running = False

        # Object classes
        self.object_classes = ["helipad", "tank" if is_simulation else "real_tank"]

        # These locks are used from threads and asyncio tasks; use threading.Lock
        # so they can be used with the synchronous 'with' statement.
        self._frame_lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        # Initialize frame processor variables
        self.frame_processor_input_lock = threading.Lock()
        self.frame_processor_input: Optional[FrameData] = None
        self.frame_processor_result_lock = threading.Lock()
        self.frame_processor_result: Optional[ProcessedResult] = None

        camera_intrinsics = self._get_camera_intrinsics(is_simulation)

        self.tracker = yolo.YoloObjectTracker(
            K=camera_intrinsics,
            model_path=(
                "nebula/controls/detection/sim.pt"
                if is_simulation
                else "nebula/controls/detection/main.pt"
            ),
        )

        controller_address, baudrate = crane_controller_address
        if not is_simulation:
            self.crane = CraneControls(
                connection_string=controller_address, baudrate=baudrate
            )

    def _get_camera_intrinsics(self, is_simulation: bool) -> Dict[str, Any]:
        if is_simulation:
            camera_intrinsics = gz.get_camera_intrinsics(
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
                world="delivery_runway",
            )
        else:
            camera_intrinsics = mission_types.get_camera_intrinsics()

        if camera_intrinsics is None:
            raise RuntimeError("Failed to get camera intrinsics")

        camera_intrinsics = camera_intrinsics.get("camera_intrinsics", None)
        if camera_intrinsics is None:
            raise RuntimeError("Camera intrinsics not found")
        return camera_intrinsics

    def _initialize_video_capture(self) -> bool:
        """Initialize video capture"""
        try:
            if self.is_simulation:
                self.cap = gz.GazeboVideoCapture()
            else:
                self.cap = cv2.VideoCapture(self.video_source)

            if not self.cap.isOpened():
                logger.error("Failed to open video source %s", self.video_source)
                return False

            logger.info("Video capture initialized successfully")
            return True

        except Exception as e:
            logger.error("Error initializing video capture: %s", e)
            return False

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

        # resize frame to 640x480 for faster transmission
        width = int(640 * frame.shape[1] // frame.shape[0])
        jpeg_frame = cv2.resize(frame, (640, int(width)))
        _, jpeg_frame = cv2.imencode(".jpg", jpeg_frame, encode_params)

        return topic, jpeg_frame.tobytes()

    async def _video_capture_loop(self):
        loop = asyncio.get_running_loop()
        while self.running:
            try:
                # Wait until capture is initialized
                if not self.cap:
                    await asyncio.sleep(0.01)
                    continue

                # call blocking cap.read() in a thread pool so we don't block the event loop
                ret, frame = await loop.run_in_executor(None, self.cap.read)
                if not ret or frame is None:
                    # brief sleep to avoid tight loop if capture fails momentarily
                    await asyncio.sleep(0.01)
                    continue

                # write copy under lock
                with self._frame_lock:
                    self._frame = frame.copy()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Error in video capture loop:\n%s", traceback.format_exc())
                await asyncio.sleep(0.1)

    def get_frame(self):
        with self._frame_lock:
            return self._frame

    async def _video_publisher_loop(self, mavlink_proxy: MAVLinkProxy):
        """Main video publishing loop"""
        if not self._initialize_video_capture():
            return

        logger.info("Video publishing started")

        frame_count = 0
        fps_timer = time.time()

        while self.running:
            try:
                frame = self.get_frame()
                if frame is None:
                    logger.warning("Failed to capture frame")
                    await asyncio.sleep(0.1)
                    continue

                # Always send raw frame (publish current raw video)
                topic, encoded_frame = self._encode_frame(frame.copy())
                await self.video_socket.send_multipart([topic, encoded_frame])

                # Submit frame for processing (non-blocking)
                data = mavlink_proxy.get_drone_data()
                if data is None:
                    logger.warning("Drone data not available, skipping frame")
                    await asyncio.sleep(0.1)
                    continue
                (
                    drone_pos,
                    drone_att,
                    ground_level,
                    mode,
                ) = data

                # Submit for processing (non-blocking)
                with self.frame_processor_input_lock:
                    self.frame_processor_input = FrameData(
                        frame=frame.copy(),
                        timestamp=time.time(),
                        drone_position=drone_pos,
                        drone_attitude=drone_att,
                        ground_level=ground_level,
                        mode=mode,
                    )

                # Check for processed previous results and send if available
                with self.frame_processor_result_lock:
                    result = self.frame_processor_result

                if result:
                    try:
                        topic, processed_frame = self._encode_frame(
                            result.processed_frame, "processed_"
                        )
                        await self.video_socket.send_multipart([topic, processed_frame])
                    except Exception:
                        logger.debug(
                            "Failed to send processed frame: %s", traceback.format_exc()
                        )

                frame_count += 1

                # FPS logging
                if time.time() - fps_timer > 5:
                    fps = frame_count / 5
                    logger.debug("Publishing video at %.1f FPS", fps)
                    frame_count = 0
                    fps_timer = time.time()

                # Small sleep to prevent CPU overload
                await asyncio.sleep(
                    CPU_BURNOUT
                )  # 30fps is sufficient for video publishing

            except Exception:
                logger.error("Error in video loop:\n%s", traceback.format_exc())
                await asyncio.sleep(0.1)

        # Cleanup
        if self.cap:
            self.cap.release()
        logger.info("Video publishing stopped")

    async def _frame_processor_loop(self):
        """Worker thread that processes frames asynchronously"""
        loop = asyncio.get_running_loop()
        while self.running:
            try:
                # Get frame data
                with self.frame_processor_input_lock:
                    frame_data = self.frame_processor_input

                if frame_data is None:
                    # nothing to process
                    await asyncio.sleep(0.01)
                    continue

                # Process in thread pool to avoid blocking
                result = await loop.run_in_executor(
                    None, self._process_frame, frame_data
                )

                if not result:
                    # brief sleep to avoid tight loop if processing failed
                    await asyncio.sleep(0.01)
                    continue

                # write copy under lock
                with self.frame_processor_result_lock:
                    if self.frame_processor_result and (
                        self.frame_processor_result.timestamp - result.timestamp > 1
                    ):
                        logger.warning("Frame processing is taking too long > 1s")
                    self.frame_processor_result = result
            except asyncio.TimeoutError:
                logger.warning("Frame processing timed out")
                await asyncio.sleep(0.01)
                continue
            except asyncio.CancelledError:
                # brief sleep to avoid tight loop if capture fails momentarily
                await asyncio.sleep(0.01)
                continue

            except Exception as e:
                logger.error("Error in frame processor worker: %s", e)
                await asyncio.sleep(0.1)

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
                        logger.info("Command: %s -> Response: %s", message, response)

            except Exception as e:
                logger.error("Error in control receiver: %s", e)
                await asyncio.sleep(0.1)

    def _handle_command(self, command: str) -> str:
        """Handle control commands"""
        command = command.strip()

        # TODO: implement the crane control logic here. './crane.py'. However, it is implemented in `in_flight` branch.
        if command == ZMQTopics.DROP_LOAD.name:
            if not self.is_simulation:
                success = self.crane.drop_load()
                return "ACK: Load dropped" if success else "NACK: Drop load failed"
            else:
                return "ACK: Load dropped"
        elif command == ZMQTopics.PICK_LOAD.name:
            if not self.is_simulation:
                success = self.crane.pick_load()
                return "ACK: Load picked" if success else "NACK: Pick load failed"
            else:
                return "ACK: Load picked"
        elif command == ZMQTopics.RAISE_HOOK.name:
            if not self.is_simulation:
                success = self.crane.manuel_yukari()
                return "ACK: Hook raised" if success else "NACK: Raise hook failed"
            else:
                return "ACK: Hook raised"
        elif command == ZMQTopics.DROP_HOOK.name:
            if not self.is_simulation:
                success = self.crane.manuel_asagi()
                return "ACK: Hook dropped" if success else "NACK: Drop hook failed"
            else:
                return "ACK: Hook dropped"
        elif command == ZMQTopics.STATUS.name:
            if not self.is_simulation:
                return "ACK: %s" % (self.crane.gather_status(),)
            else:
                return "ACK: Simulation mode - no crane status"

        elif command == ZMQTopics.HELIPAD_GPS.name:
            with self.frame_processor_result_lock:
                if (
                    self.frame_processor_result
                    and self.frame_processor_result.gps_coordinates
                    and "helipad" in self.frame_processor_result.gps_coordinates
                ):
                    coords = self.frame_processor_result.gps_coordinates["helipad"]
                    return "ACK>%s,%s" % (coords[0], coords[1])
                else:
                    return "NACK: No GPS data available"
        elif command == ZMQTopics.TANK_GPS.name:
            tank_key = "tank" if self.is_simulation else "real_tank"
            with self.frame_processor_result_lock:
                if (
                    self.frame_processor_result
                    and self.frame_processor_result.gps_coordinates
                    and tank_key in self.frame_processor_result.gps_coordinates
                ):
                    coords = self.frame_processor_result.gps_coordinates[tank_key]
                    return "ACK>%s,%s" % (coords[0], coords[1])
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
        self.video_socket.bind(f"tcp://*:{self.video_port}")

        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(f"tcp://*:{self.control_port}")

        self.running = True
        logger.info("Server started")

        # Run both loops concurrently
        await asyncio.gather(
            self._video_publisher_loop(mavlink_proxy),
            self._control_receiver_loop(),
            self._video_capture_loop(),
            self._frame_processor_loop(),
        )

    def stop(self):
        """Stop the server"""
        logger.info("Stopping server...")
        self.running = False

        # Stop clear heavy variables
        del self.frame_processor_input
        del self.frame_processor_result
        del self._frame

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
    parser.add_argument(
        "--crane-controller-address",
        type=str,
        default="/dev/ttyUSB1",
        help="Crane controller address (e.g., /dev/ttyUSB1)",
    )

    parser.add_argument(
        "--crane-controller-baudrate",
        type=int,
        default=57600,
        help="Crane controller baudrate",
    )

    args = parser.parse_args()

    # Convert video_source to int if it's a number
    try:
        args.video_source = int(args.video_source)
    except ValueError:
        pass

    # Initialize MAVLink proxy
    connection_string = "udp:127.0.0.1:14550" if args.is_simulation else "/dev/ttyUSB0"
    mavlink_proxy = MAVLinkProxy(connection_string)

    # Enable video streaming for simulation
    if args.is_simulation:
        logger.info("Enabling video streaming for simulation")
        done = gz.enable_streaming(
            world="delivery_runway",
            model_name="iris_with_stationary_gimbal",
            camera_link="tilt_link",
        )
        if not done:
            logger.error("Failed to enable streaming")
            return

    # Initialize server
    server = ZMQServer(
        video_port=args.video_port,
        control_port=args.control_port,
        crane_controller_address=(args.crane_controller_address, 57600),
        video_source=args.video_source,
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
