#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import signal
import time
import traceback
from typing import Optional, Tuple

import cv2
import zmq
import zmq.asyncio

from src.controls.detection import yolo
from src.controls.mavlink import ardupilot, gz, mission_types
from src.mq.crane import ZMQTopics
from src.mq.video_writer import get_video_writer

# Configuration constants
CPU_SLEEP_INTERVAL = 0.05
# FRAME_PROCESS_INTERVAL = 3  # Process every 3rd frame for 10fps
MAX_FRAME_WIDTH = 640
DATA_TIMEOUT_THRESHOLD = 2  # seconds
FPS_LOG_INTERVAL = 5  # seconds

# Setup logging
log_file = os.path.join(os.path.expanduser("~"), "local_zmq_server.log")
logger = logging.getLogger("local-zmq-server")
logger.setLevel(logging.DEBUG)

if not logger.hasHandlers():
    formatter = logging.Formatter("%(asctime)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class LocalZMQServer:
    """Local ZMQ server for video processing and control commands"""

    def __init__(
        self,
        video_output: str,
        video_source: int | str,
        control_address: int = 5556,
        is_simulation: bool = False,
        object_classes=("helipad", "tank"),
    ):
        self.control_address = control_address
        self.video_source = video_source
        self.video_output = video_output
        self.is_simulation = is_simulation
        self.object_classes = object_classes
        self.running = False

        # ZMQ setup
        self.context = zmq.asyncio.Context()
        self.control_socket = None

        # Video components
        self.cap = None
        self.video_writer = None

        # State management
        self.last_result: Optional[mission_types.ProcessedResult] = None
        self.frame_skip_counter = 0

        # Initialize object tracker
        self._setup_tracker()

    def _setup_tracker(self):
        """Initialize YOLO object tracker with camera parameters"""
        try:
            if self.is_simulation:
                camera_intrinsics = gz.get_camera_params(
                    model_name="iris_with_stationary_gimbal",
                    camera_link="tilt_link",
                    world="delivery_runway",
                )
            else:
                camera_intrinsics = mission_types.get_camera_params()

            if not camera_intrinsics or "camera_intrinsics" not in camera_intrinsics:
                raise RuntimeError("Failed to get camera intrinsics")

            model_path = (
                "src/controls/detection/sim.pt"
                if self.is_simulation
                else "src/controls/detection/main.pt"
            )
            config = mission_types.get_config()

            self.drone_client = ardupilot.ArdupilotConnection(
                connection_string=config.mavproxy_source,
                logger=logger,
                wait_heartbeat=True,
            )

            self.tracker = yolo.YoloObjectTracker(
                K=camera_intrinsics["camera_intrinsics"],
                model_path=model_path,
            )
            logger.info("Object tracker initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize tracker: {e}")
            raise

    def _initialize_video_components(self) -> bool:
        """Initialize video capture and writer"""
        try:
            # Initialize video capture
            self.cap = cv2.VideoCapture(self.video_source)

            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.video_source}")
                return False

            # Get video properties
            width = MAX_FRAME_WIDTH  # int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                / int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                * 640
            )
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 10

            # Initialize video writer
            self.video_writer = get_video_writer(
                source=self.video_output,
                width=width,
                height=height,
                fps=self.fps,  # TODO: 10
            )

            logger.info(
                f"Video initialized: {self.video_output} ({width}x{height} @ {self.fps}fps)"
            )
            return True

        except Exception as e:
            logger.error(f"Video initialization error: {e}")
            return False

    def _fetch_gps_data(self) -> Optional[Tuple[float, float, float]]:
        """Fetch GPS data from the drone"""
        if not self.drone_client:
            logger.error("Drone client not initialized")
            return None

        try:
            return self.drone_client.get_frame_data()
        except Exception as e:
            logger.error(f"Failed to fetch GPS data: {e}")
            return None

    async def _fetch_gps_data_loop(self):
        """Continuously fetch GPS data from the drone"""
        while self.running:
            self.drone_client.get_status()
            await asyncio.sleep(1)

    async def _video_processing_loop(self):
        """Main video processing and publishing loop"""
        if not self._initialize_video_components():
            return

        logger.info("Video processing started")
        frame_count = 0
        fps_timer = time.time()
        prev_frame_hash = None

        while self.running:
            try:
                # Capture frame
                if not self.cap or not self.cap.isOpened():
                    logger.error("Video capture not available")
                    await asyncio.sleep(1)
                    continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("Failed to capture frame")
                    await asyncio.sleep(0.1)
                    continue

                gps_data = self._fetch_gps_data()
                if not gps_data:
                    logger.error(f"Failed to fetch GPS data")
                    await asyncio.sleep(0.1)
                    continue

                # Skip duplicate frames
                current_hash = hash(frame.tobytes())
                if prev_frame_hash == current_hash:
                    logger.debug("Duplicate frame skipped")
                    await asyncio.sleep(0.1)
                    continue
                prev_frame_hash = current_hash

                now = time.time()
                if (
                    now - gps_data.timestamp > 2
                ):  # if the frame capture is within 2 second delay
                    logger.warning(
                        f"Frame and data are too far apart for processing... {int(now - gps_data.timestamp)}s"
                    )

                # Process frame (returns None for skipped frames)
                # Resize frame if too large
                data = mission_types.FrameData(
                    drone_attitude=gps_data.drone_attitude,
                    drone_position=gps_data.drone_position,
                    ground_level=gps_data.ground_level,
                    mode=gps_data.mode,
                    timestamp=time.time(),
                    frame=self._resize_frame(frame.copy()),
                )

                # Process frame with skipping logic
                processed_result = await self._process_frame_data(data)
                if processed_result and self.video_writer:
                    self.video_writer.write(processed_result.processed_frame)
                    self.last_result = processed_result._replace(processed_frame=None)

                # Performance monitoring
                frame_count += 1
                if time.time() - fps_timer > FPS_LOG_INTERVAL:
                    self.fps = frame_count / FPS_LOG_INTERVAL
                    logger.debug(f"Processing at {self.fps:.1f} FPS")
                    frame_count = 0
                    fps_timer = time.time()

                await asyncio.sleep(CPU_SLEEP_INTERVAL)

            except Exception as e:
                logger.error(f"Video processing error: {e}")
                print(traceback.format_exc())
                await asyncio.sleep(0.1)

        logger.info("Video processing stopped")

    def _resize_frame(self, frame):
        """Resize frame to optimize processing"""
        height, width = frame.shape[:2]
        if width > MAX_FRAME_WIDTH:
            scale = MAX_FRAME_WIDTH / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
        return frame

    async def _process_frame_data(
        self, frame_data: mission_types.FrameData
    ) -> Optional[mission_types.ProcessedResult]:
        """Process frame asynchronously for object detection"""
        try:
            # Process with YOLO tracker
            processed_frame, gps_coords, pixel_coords = self.tracker.process_frame(
                frame=frame_data.frame,
                drone_gps=frame_data.drone_position,
                drone_attitude=frame_data.drone_attitude,
                ground_level_masl=frame_data.ground_level,
                object_classes=self.object_classes,
            )

            # Add annotations to frame
            annotated_frame = self.tracker.write_on_frame(
                frame=processed_frame,
                curr_gps=frame_data.drone_position,
                gps_coords=gps_coords,
                pixel_coords=pixel_coords,
                mode=frame_data.mode,
                object_classes=self.object_classes,
            )

            return mission_types.ProcessedResult(
                processed_frame=annotated_frame,
                gps_coordinates=gps_coords,
                pixel_coordinates=pixel_coords,
                timestamp=frame_data.timestamp,
            )

        except Exception as e:
            logger.warning(f"Frame processing failed: {e}")
            return None

    async def _control_loop(self):
        """Handle incoming control commands"""
        logger.info("Control receiver started")

        while self.running:
            try:
                if await self.control_socket.poll(timeout=100):
                    message = await self.control_socket.recv_string()
                    response = self._handle_command(message.strip())
                    await self.control_socket.send_string(response)

                    if "NACK" not in response:
                        logger.info(f"Command: {message} -> Response: {response}")

            except Exception as e:
                logger.error(f"Control loop error: {e}")
                await asyncio.sleep(0.1)

        logger.info("Control receiver stopped")

    def _handle_command(self, command: str) -> str:
        """Process control commands and return responses"""
        latest_gps = {}
        if self.last_result:
            latest_gps = self.last_result.gps_coordinates

        if command == ZMQTopics.HELIPAD_GPS.name:
            if latest_gps and "helipad" in latest_gps:
                coords = latest_gps["helipad"]
                return f"ACK>{coords[0]},{coords[1]}"
            return "NACK: No helipad GPS data available"

        elif command == ZMQTopics.TANK_GPS.name:
            tank_key = "tank" if self.is_simulation else "real_tank"
            if latest_gps and tank_key in latest_gps:
                coords = latest_gps[tank_key]
                return f"ACK>{coords[0]},{coords[1]}"
            return "NACK: No tank GPS data available"
        elif command == ZMQTopics.FPS.name:
            return f"ACK>{self.fps}"
        else:
            return "NACK: Controller not initialized"

    async def start(self):
        """Start the server with all components"""
        if self.running:
            logger.warning("Server already running")
            return

        # Initialize control socket
        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(self.control_address)

        self.running = True
        logger.info(f"Server started on port {self.control_address}")

        try:
            # Run video processing and control loops concurrently
            await asyncio.gather(
                self._fetch_gps_data_loop(),
                self._video_processing_loop(),
                self._control_loop(),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up resources...")
        self.running = False

        # Close video components
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.close()

        # Close ZMQ components
        if self.control_socket:
            self.control_socket.close()
        self.context.term()
        self.drone_client.close()

        # Clear references
        self.last_result = None
        logger.info("Cleanup complete")

    def stop(self):
        """Stop the server"""
        self.running = False


##############################################################################################

##############################################################################################


async def main():
    parser = argparse.ArgumentParser(description="Optimized ZMQ Video Server")
    parser.add_argument(
        "--is-simulation", action="store_true", help="Run in simulation mode"
    )
    args = parser.parse_args()

    # Load configuration
    config = mission_types.get_config()
    logger.info(f"Configuration loaded: {config}")

    # Enable simulation video streaming if needed
    if args.is_simulation:
        gz_config = mission_types.get_gazebo_config()
        logger.info("Enabling simulation video streaming")

        if not gz.enable_streaming(
            world=gz_config.world,
            model_name=gz_config.model_name,
            camera_link=gz_config.camera_link,
        ):
            logger.error("Failed to enable streaming")
            return

    # Set object classes based on mode
    object_classes = (
        ["helipad", "tank"] if args.is_simulation else ["real_helipad", "real_tank"]
    )

    # Initialize server
    server = LocalZMQServer(
        control_address=config.control_address,
        video_source=config.video_source,
        video_output="ipc:///tmp/video.sock",  # "rtsp://localhost:8554/processed",
        is_simulation=gz_config.is_simulation,
        object_classes=object_classes,
    )

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()
        server.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: signal_handler())

    try:
        logger.info("Starting server. Press Ctrl+C to stop.")

        # Create server task
        server_task = asyncio.create_task(server.start())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Wait for completion or shutdown
        _, pending = await asyncio.wait(
            [server_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        await server.cleanup()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
