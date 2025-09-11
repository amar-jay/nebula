#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import signal
import time
import traceback
from typing import Optional

import cv2
import numpy as np
import zmq
import zmq.asyncio

from src.controls.detection import yolo
from src.controls.logger import init_logging
from src.controls.mavlink import ardupilot, gz, mission_types
from src.mq.crane import ZMQTopics
from src.mq.video_writer import get_video_writer

# Configuration constants
CPU_SLEEP_INTERVAL = 0.05
FRAME_PROCESS_INTERVAL = 1  # Process every 3rd frame for 10fps
MAX_FRAME_WIDTH = 640
DATA_TIMEOUT_THRESHOLD = 2  # seconds
FPS_LOG_INTERVAL = 5  # seconds

# Setup logging
logger = init_logging(
    level=logging.INFO,
    log_file=os.path.join(os.path.expanduser("~"), "local-zmq-server.log"),
)


class LocalZMQServer:
    """Local ZMQ server for video processing and control commands"""

    def __init__(
        self,
        video_output: str,
        video_source: int | str,
        mavproxy_source: str,
        control_address: str,
        is_simulation: bool = False,
        object_classes=("helipad", "tank"),
        dataset_path: Optional[str] = None,
    ):
        self.control_address = control_address
        self.video_source = video_source
        self.video_output = video_output
        self.mavproxy_source = mavproxy_source
        self.is_simulation = is_simulation
        self.object_classes = object_classes
        self.dataset_path = dataset_path
        self.running = False

        # ZMQ setup
        self.context = zmq.asyncio.Context()
        self.control_socket = None

        # Video components
        self.cap = None
        self.video_writer = None
        self.frame_data: Optional[mission_types.FrameData] = None

        # State management
        self.last_result: Optional[mission_types.ProcessedResult] = None
        self.frame_skip_counter = 0
        self.fps = 0
        self.frame = None
        self.frame_timestamp = None
        self.video_dims = None

        # Initialize object tracker
        self._setup_tracker()
        self._initialize_video_components()
        # logger.error("Failed to initialize video components")
        # return

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
                else "src/controls/detection/best.pt"
            )

            self.drone_client = ardupilot.ArdupilotConnection(
                connection_string=self.mavproxy_source,
                logger=logger,
                wait_heartbeat=True,
            )
            print(model_path, "<- model_path")

            self.tracker = yolo.YoloObjectTracker(
                K=camera_intrinsics["camera_intrinsics"],
                model_path=model_path,
            )
            # if self.dataset_path:
            #     self.dataset = self.tracker.dataset_writer(self.dataset_path)
            logger.success("Object tracker initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize tracker: {e}")
            raise

    def _initialize_video_components(self) -> bool:
        """Initialize video capture and writer"""
        if self.cap:
            return True
        try:
            # Initialize video capture
            if (
                not self.is_simulation
                and isinstance(self.video_source, str)
                and self.video_source.startswith("rtsp")
            ):
                pipeline = (
                    f"rtspsrc location={self.video_source} latency=0 ! "
                    "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink"
                )
                self.cap = cv2.VideoCapture(
                    pipeline, cv2.CAP_GSTREAMER
                )  # pylint: disable=E1101
            elif self.is_simulation:
              return gz.GazeboVideoCapture()
            else:
                self.cap = cv2.VideoCapture(self.video_source)  # pylint: disable=E1101

            if not self.cap.isOpened():
                logger.error(
                    f"Failed to open video source: {self.video_source if self.video_source.startswith('rtsp') else self.video_source}"
                )
                return False

            # Get video properties
            # pylint: disable=E1101
            self.video_dims = (
                MAX_FRAME_WIDTH,
                int(
                    int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    / int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    * MAX_FRAME_WIDTH
                ),
            )
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 10

            # Initialize video writer
            self.video_writer = get_video_writer(
                source=self.video_output,
                width=self.video_dims[0],
                height=self.video_dims[1],
                fps=int(self.fps / FRAME_PROCESS_INTERVAL),
            )

            logger.success(
                f"Video initialized: {self.video_output} ({self.video_dims[0]}x{self.video_dims[1]} @ {self.fps}fps)"
            )
            return True

        except Exception as e:
            logger.error(f"Video initialization error: {e}")
            return False

    async def _fetch_gps_data_loop(self):
        """Continuously fetch GPS data from the drone"""

        while not self.drone_client:
            logger.error("Drone client not initialized")
            await asyncio.sleep(1)
            continue
        logger.success("GPS data fetch loop started")
        while self.running:
            status = self.drone_client.get_status(0.1)
            if (
                status["position_int"] is None
                or not status["position_int"].get("lat", None)
                or not status.get("orientation_rad", {}).get("yaw", None)
            ):
                logger.error("MAVLink connection GPS telemetry error")
                await asyncio.sleep(1)
                continue

            pos: dict[str, float] = status["position_int"]
            att: dict[str, float] = status["orientation_rad"]
            if pos is None or att is None:
                logger.error("Incomplete GPS or attitude data")
                await asyncio.sleep(1)
                continue
            lat = pos["lat"] / 1e7
            lon = pos["lon"] / 1e7
            relative_alt = pos["alt"] / 1000.0  # meters
            roll = att["roll"]
            pitch = att["pitch"]
            yaw = att["yaw"]
            if yaw < 0:
                yaw += 2 * np.pi
            self.frame_data = mission_types.FrameData(
                frame=None,
                mode=status["mode"],
                drone_position=(lat, lon, relative_alt),
                drone_attitude=(roll, pitch, yaw),
                timestamp=status["timestamp"],
            )
            await asyncio.sleep(0.05)

    async def _video_receiver_loop(self):
        if not self._initialize_video_components():
            logger.error("Failed to initialize video components")
            return

        if not self.cap:
            logger.error("Video capture not available")
            await asyncio.sleep(1)
            return
        logger.success("Video receiver loop started")

        while self.running:
            if not self.cap:
                logger.error("Video capture not available")
                await asyncio.sleep(1)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.error("Failed to capture frame")
                await asyncio.sleep(0.1)
                continue
            self.frame = frame
            self.frame_timestamp = time.time()
            cv2.waitKey(1)  # pylint: disable=E1101
            await asyncio.sleep(0.01)

    async def _video_processing_loop(self):
        """Main video processing and publishing loop"""
        logger.warning("Starting video processing...")
        if not self._initialize_video_components():
            return
        frame_count = 0
        fps_timer = time.time()
        prev_frame_hash = None
        counter = 0

        # while not self.frame_data:
        #     logger.warning("No GPS data available yet...")
        #     await asyncio.sleep(1)
        #     continue

        logger.success("Video Processing Loop started")
        now = time.time()
        while self.running:
            try:
                if self.frame is None:
                    logger.warning("Failed to get frame")
                    await asyncio.sleep(1)
                    continue
                logger.debug(f"1. Got a frame at {str((time.time() - now) * 1000)} ms")

                frame = self.frame
                gps_data = self.frame_data
                if not gps_data:
                    logger.warning("No GPS data available")
                    gps_data = mission_types.FrameData(
                      frame=self.frame,
                      drone_attitude=(0,0,0),
                      drone_position=(0,0,0),
                      timestamp=time.time()
                    )
                logger.debug(f"2. Got GPS data at {str((time.time() - now) * 1000)} ms")

                # Skip duplicate frames
                current_hash = hash(frame.tobytes())
                if prev_frame_hash == current_hash:
                    logger.warning("Duplicate frame skipped")
                    await asyncio.sleep(1)
                    continue
                prev_frame_hash = current_hash

                now = time.time()
                if (
                    now - gps_data.timestamp > 2
                    or now - self.frame_timestamp > 2
                    or abs(self.frame_timestamp - gps_data.timestamp) > 2
                ):  # if the frame capture is within 1 second delay
                    logger.warning(
                        f"Frame and data are too far apart for processing... {int(now - gps_data.timestamp)}s"
                    )

                gps_data.frame = frame.copy()
                gps_data.timestamp = time.time()

                # Process frame with skipping logic
                if counter >= FRAME_PROCESS_INTERVAL:
                    processed_result = await self._process_frame_data(gps_data)
                    logger.debug(
                        f"3. Processed frame at {str((time.time() - now) * 1000)} ms"
                    )
                    if processed_result and self.video_writer:
                        self.video_writer.write(processed_result.processed_frame)
                        logger.debug(
                            f"4. Wrote frame at {str((time.time() - now) * 1000)} ms"
                        )
                        cv2.waitKey(1)
                        self.last_result = processed_result
                        if self.last_result:
                            self.last_result.processed_frame = None
                    if (
                        self.is_simulation
                        and hasattr(self, "dataset")
                        and self.dataset
                        and processed_result
                    ):
                        helipad_key = self.object_classes[0]
                        self.dataset(
                            pixel=processed_result.pixel_coordinates.get(
                                helipad_key, (None, None)
                            ),
                            gps_true=gps_data.drone_position,
                            attitude_true=gps_data.drone_attitude,
                            gps_estimated=processed_result.gps_coordinates.get(
                                helipad_key, (None, None)
                            ),
                            timestamp=processed_result.timestamp,
                        )
                    counter = 0
                counter += 1

                # Performance monitoring
                frame_count += 1
                if time.time() - fps_timer > FPS_LOG_INTERVAL:
                    self.fps = frame_count / FPS_LOG_INTERVAL
                    logger.debug(f"Processing at {self.fps:.1f} FPS")
                    frame_count = 0
                    fps_timer = time.time()

                await asyncio.sleep(CPU_SLEEP_INTERVAL)
                # print("Duration: ", time.time()-now)

            except Exception as e:
                logger.error(f"Video processing error: {e}")
                logger.debug(traceback.format_exc())
                await asyncio.sleep(0.1)

        logger.info("Video processing stopped")

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
                fps=self.fps,
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
        logger.success("Control receiver started")

        while self.running:
            try:
                if await self.control_socket.poll(timeout=100):
                    message = await self.control_socket.recv_string()
                    response = self._handle_command(message.strip())
                    await self.control_socket.send_string(response)

                    if "NACK" not in response:
                        logger.info(f"Command: {message} -> Response: {response}")
            except zmq.Again:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Control loop error: {e}{traceback.format_exc()}")
                await asyncio.sleep(0.1)

        logger.info("Control receiver stopped")

    def _handle_command(self, command: str) -> str:
        """Process control commands and return responses"""
        if self.last_result is None:
            return "NACK: No processed data available yet"

        latest_gps = self.last_result.gps_coordinates
        if not latest_gps:
            return "NACK: No GPS data available"

        if command == ZMQTopics.HELIPAD_GPS.name:
            heli_key = self.object_classes[0]
            if "helipad" not in heli_key:
                logger.error(f"Invalid helipad key: {heli_key}")
                return "NACK: Errors with the keys. Please check the server code."
            elif heli_key not in latest_gps:
                logger.error(f"Helipad key '{heli_key}' not found in latest GPS data")
                return "NACK: No helipad GPS data available"
            elif latest_gps:
                logger.debug(f"Latest Helipad GPS data: {latest_gps[heli_key]}")
                coords = latest_gps[heli_key]
                return f"ACK>{coords[0]},{coords[1]}"
            return "NACK: No helipad GPS data available"

        elif command == ZMQTopics.TANK_GPS.name:
            tank_key = self.object_classes[1]
            if "tank" not in tank_key:
                logger.error(f"Invalid tank key: {tank_key}")
                return "NACK: Errors with the keys. Please check the server code."
            elif tank_key not in latest_gps:
                logger.error(f"Tank key '{tank_key}' not found in latest GPS data")
                return "NACK: No tank GPS data available"
            elif latest_gps:
                logger.debug(f"Latest Tank GPS data: {latest_gps[tank_key]}")
                coords = latest_gps[tank_key]
                return f"ACK>{coords[0]},{coords[1]}"
            return "NACK: No tank GPS data available"
        elif command == ZMQTopics.FPS.name:
            logger.debug(f"Current FPS: {self.fps}")
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
                self._video_receiver_loop(),
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

        self.tracker.close()
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
    parser = argparse.ArgumentParser(description="Local ZMQ Video Server")

    parser.add_argument(
        "--config-path",
        choices=["config/default.yaml", "config/simulation.yaml"],
        default="config/default.yaml",
        help="Path to the configuration file",
    )
    args = parser.parse_args()

    config = mission_types.get_config(args.config_path)
    gz_config = mission_types.get_gazebo_config(args.config_path)

    # Load configuration
    logger.info(f"Configuration loaded:\n{config}")

    # Enable simulation video streaming if needed
    if gz_config.is_simulation:
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
        ["helipad", "tank"] if gz_config.is_simulation else ["helipad", "real_tank"]
    )

    # Initialize server
    server = LocalZMQServer(
        video_source=config.video_source,
        video_output=config.video_output,  # "rtsp://localhost:8554/processed",
        mavproxy_source=config.mavproxy_source,
        control_address=config.control_address,
        is_simulation=gz_config.is_simulation,
        dataset_path=config.dataset_path if len(config.dataset_path) > 0 else None,
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