#!/usr/bin/env python3
# pylint: disable=I1101

import argparse
import asyncio

# import gc  # For garbage collection
import logging
import os
import signal
import time
import traceback
from typing import Dict, Optional, Tuple

import cv2
import zmq
import zmq.asyncio

from src.controls.detection import yolo
from src.controls.mavlink import gz, mission_types
from src.mq.crane import CraneControls, ZMQTopics
from src.mq.mavproxy_tcp import MAVLinkProxy
from src.mq.video_writer import RTSPVideoWriter

# ignore opencv warnings
# os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

# IMAGE_QUALITY = 50  # JPEG quality for video frames
CPU_BURNOUT = 0.05  # Increased CPU burn rate for better memory management
FRAME_BUFFER_SIZE = 1  # Limit frame buffer size

SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


# Add success() method to Logger
def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)  # pylint: disable=W0212


logging.Logger.success = success

log_file = os.path.join(os.path.expanduser("~"), "zmq_server.log")

logger = logging.getLogger("zmq-server")
logger.setLevel(logging.DEBUG)  # Ensure logger level is set

if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(file_handler)


class ZMQServer:
    """ZMQ server that publishes video and handles control commands"""

    def __init__(
        self,
        video_output: str,
        controller_connection_string: Optional[str],
        control_port: int = 5556,
        video_source: int | str = 0,
        is_simulation: bool = False,
        controller_baudrate: int = 9600,
        object_classes=("helipad", "tank"),
    ):
        self.control_port = control_port
        self.video_source = video_source
        self.video_output = video_output
        self.is_simulation = is_simulation

        # Initialize controller
        if controller_connection_string is None:
            logger.warning(
                "Controller connection string not provided, so controller will not be used."
            )
            self.controller = None
        else:
            self.controller = CraneControls(
                connection_string=controller_connection_string,
                baudrate=controller_baudrate,
            )

        # ZMQ Context
        self.context = zmq.asyncio.Context()

        # Sockets
        self.control_socket = None

        # Video capture and writer
        self.cap = None
        self.video_writer = None

        # State
        # self.hook_state = "dropped"
        self.running = False  # TODO: WHAT??

        # Latest processed results
        # # self.latest_gps_coordinates = {}
        # self.latest_pixel_coordinates = {}
        self.last_result: Optional[mission_types.ProcessedResult] = None

        # Object classes
        self.object_classes = object_classes

        if is_simulation:
            camera_intrinsics = gz.get_camera_params(
                model_name="iris_with_stationary_gimbal",
                camera_link="tilt_link",
                world="delivery_runway",
            )
        else:
            camera_intrinsics = mission_types.get_camera_params()

        if camera_intrinsics is None:
            raise RuntimeError("Failed to get camera intrinsics")

        camera_intrinsics = camera_intrinsics.get("camera_intrinsics", None)
        if camera_intrinsics is None:
            raise RuntimeError("Camera intrinsics not found")

        self.tracker = yolo.YoloObjectTracker(
            K=camera_intrinsics,
            model_path="src/controls/detection/sim.pt"
            if is_simulation
            else "src/controls/detection/main.pt",
        )

        # Initialize frame processor params
        self.skip_counter = 0
        self.process_every_n_frames = (
            3  # Process every 3rd frame to maintain performance, setting it to 10fps
        )

    def _initialize_video_capture(self) -> bool:
        """Initialize video capture and video writer"""
        try:
            if self.is_simulation:
                self.cap = gz.GazeboVideoCapture(fps=10)
            else:
                self.cap = cv2.VideoCapture(self.video_source)

            if not self.cap.isOpened():
                logger.error("Failed to open video source %s", self.video_source)
                return False

            # Get video properties for video writer
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # // 2
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # // 2
            fps = (
                int(self.cap.get(cv2.CAP_PROP_FPS)) or 30
            )  # Default to 30 FPS if unable to get

            # Initialize video writer
            self.video_writer = RTSPVideoWriter(
                source=self.video_output,
                width=width,
                height=height,
                fps=10,
            )

            logger.info("Video capture and writer initialized successfully")
            logger.info(
                "Video output: %s (%dx%d @ %d FPS)",
                self.video_output,
                width,
                height,
                fps,
            )
            return True

        except Exception as e:
            logger.error("Error initializing video capture: %s", e)
            return False

    async def _video_publisher_loop(self, mavlink_proxy: MAVLinkProxy):
        """Main video processing loop - only sends processed frames"""
        if not self._initialize_video_capture():
            return

        logger.info("Video publishing started")

        frame_count = 0
        fps_timer = time.time()
        prev_frame = None

        while self.running:
            try:
                if not self.cap or not self.cap.isOpened():
                    logger.error("Video capture not initialized or opened")
                    await asyncio.sleep(1)
                    continue
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("Failed to capture frame")
                    await asyncio.sleep(0.1)
                    continue
                # TODO: check if the frames are the same (debug)
                if prev_frame is not None and (prev_frame == frame).all():
                    logger.warning("Duplicate frame detected, skipping processing")
                    await asyncio.sleep(1)
                    continue
                prev_frame = frame.copy()

                # Process frame for object detection
                data = mavlink_proxy.get_drone_data()
                if data is None:
                    logger.warning("No drone data available, skipping frame")
                    await asyncio.sleep(1)
                    continue

                # TODO: Resize frame to reduce memory usage
                height, width = frame.shape[:2]
                if width > 640:  # Limit frame size to reduce memory
                    scale = 640 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))

                now = time.time()
                if (
                    now - data.timestamp > 2
                ):  # if the frame capture is within 2 second delay
                    logger.warning(
                        f"Frame and data are too far apart for processing... {int(now - data.timestamp)}s"
                    )

                # Process frame (returns None for skipped frames)
                data.frame = frame.copy()

                # Remove cv2.imshow calls that cause memory accumulation
                processed_result = self._process_frame(data)
                del data.frame  # Clear frame reference to free memory

                if hasattr(processed_result, "processed_frame"):
                    # Write processed frame to video output
                    if self.video_writer:
                        # cv2.imshow("Processed Frame", processed_result.processed_frame)
                        self.video_writer.write(processed_result.processed_frame)
                    # Clean up frame references to free memory
                    processed_result.processed_frame = None
                    self.last_result = processed_result

                # Explicitly delete frame reference to free memory
                del frame
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

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt in video loop, shutting down...")
                self.running = False
                break
            except Exception:
                logger.error("Error in video loop:\n%s", traceback.format_exc())
                await asyncio.sleep(0.1)

        logger.info("Video publisher loop stopped")
        self.running = False
        logger.info("Closing video writer...")
        await asyncio.sleep(0.1)  # Allow time for cleanup
        logger.info("Video writer closed")
        # Cleanup
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.close()
        logger.info("Video writer closed")

    async def _control_receiver_loop(self):
        """Control command receiver loop"""
        logger.info("Control receiver started")

        try:
            while self.running:
                try:
                    # Check for messages with timeout
                    if await self.control_socket.poll(timeout=100):
                        message = await self.control_socket.recv_string()
                        response = self._handle_command(message)
                        await self.control_socket.send_string(response)
                        if "NACK" not in message:
                            logger.info(
                                "Command: %s -> Response: %s", message, response
                            )

                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt in control loop, shutting down...")
                    self.running = False
                    break
                except Exception as e:
                    logger.error("Error in control receiver: %s", e)
                    traceback.print_exc()
                    await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt in control receiver loop")
            self.running = False

    def _handle_command(self, command: str) -> str:
        """Handle control commands"""
        command = command.strip()
        latest_gps, _ = self.get_last_coordinates()
        if command == ZMQTopics.HELIPAD_GPS.name:
            if latest_gps and "helipad" in latest_gps:
                coords = latest_gps["helipad"]
                return f"ACK>{coords[0]},{coords[1]}"
            else:
                return "NACK: No GPS data available"
        elif command == ZMQTopics.TANK_GPS.name:
            tank_key = "tank" if self.is_simulation else "real_tank"
            if latest_gps and tank_key in latest_gps:
                coords = latest_gps[tank_key]
                return f"ACK>{coords[0]},{coords[1]}"
            else:
                return "NACK: No GPS data available"
        else:
            if self.controller is None:
                return "NACK: Controller not initialized"
            return self.controller.handle_command(command)

    async def start(self, mavlink_proxy: MAVLinkProxy):
        """Start the server"""
        if self.running:
            logger.warning("Server is already running")
            return

        # Initialize ZMQ control socket only
        self.control_socket = self.context.socket(zmq.REP)
        self.control_socket.bind(self.control_port)

        self.running = True
        logger.info(f"Control socket bound to {self.control_port}")

        try:
            # Run both loops concurrently
            await asyncio.gather(
                self._video_publisher_loop(mavlink_proxy),
                self._control_receiver_loop(),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Error in server loops: {e}")
        finally:
            self.running = False

    def _process_frame(
        self, frame_data: mission_types.FrameData
    ) -> Optional[mission_types.ProcessedResult]:
        """Process frame with smart skipping to maintain performance"""

        try:
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
                logger.error("Error writing on frame: %s", traceback.format_exc())
                processed_frame = frame_data.frame.copy()

            # Remove debug print and cv2.imshow to prevent meimory leaks
            # print(gps_coords)
            # cv2.imshow("Annotated Frame", processed_frame)
            # if cv2.waitKey(1) & 0xFF == ord("q"):
            #     raise KeyboardInterrupt

            result = mission_types.ProcessedResult(
                processed_frame=processed_frame,
                gps_coordinates=gps_coords,
                pixel_coordinates=pixel_coords,
                timestamp=frame_data.timestamp,
            )

            # self.last_result = result
            return result

        except Exception as e:
            logger.warning("Frame processing failed: %s", e)
            # Clean up any remaining frame references
            # gc.collect()
            return None

        # Return None for skipped frames
        # return self.last_result

    def get_last_coordinates(
        self,
    ) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, Tuple[int, int]]]:
        """Get the last processed coordinates"""
        if self.last_result:
            return self.last_result.gps_coordinates, self.last_result.pixel_coordinates
        return {}, {}

    def close(self):
        """Stop the server"""
        logger.info("Stopping server...")
        self.running = False

        # Close sockets
        try:
            if self.control_socket:
                self.control_socket.close()
        except Exception as e:
            logger.error(f"Error closing control socket: {e}")

        # Close video capture and writer
        try:
            if self.cap:
                self.cap.release()
        except Exception as e:
            logger.error(f"Error closing video capture: {e}")

        # Close video writer
        try:
            if self.video_writer:
                self.video_writer.close()
        except Exception as e:
            logger.error(f"Error closing video writer: {e}")

        # Clear any remaining frame references
        self.last_result = None
        #
        # gc.collect()

        # Terminate context
        try:
            self.context.term()
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}")

        logger.info("Server stopped")


async def main():
    parser = argparse.ArgumentParser(description="ZMQ Video Server")
    parser.add_argument(
        "--is-simulation", action="store_true", help="Run in simulation mode"
    )

    args = parser.parse_args()
    config = mission_types.get_server_config()
    print("Configuration loaded:\n", config)

    # Convert video_source to int if it's a number

    # Initialize MAVLink proxy
    mavlink_proxy = MAVLinkProxy(
        config.mavproxy_source,
        host=config.mavproxy_dest_host,
        port=config.mavproxy_dest_port,
        logger=logger,
    )

    # Enable video streaming for simulation
    if args.is_simulation:
        gz_config = mission_types.get_gazebo_config()
        logger.info("Enabling video streaming for simulation")
        done = gz.enable_streaming(
            world=gz_config.world,
            model_name=gz_config.model_name,
            camera_link=gz_config.camera_link,
        )
        if not done:
            logger.error("Failed to enable streaming")
            return

    object_classes = ["real_helipad", "real_tank"]
    if args.is_simulation:
        object_classes = ["helipad", "tank"]
    # Initialize server
    server = ZMQServer(
        control_port=config.control_address,
        video_source=config.video_source,
        video_output="rtsp://localhost:8554/processed",  # config.sandwich_video_pipe,
        # video_output="rtsp://192.168.1.113:8554/processed",
        is_simulation=args.is_simulation,
        controller_connection_string=config.controller_connection_string,
        controller_baudrate=config.controller_baudrate,
        object_classes=object_classes,
    )

    mavlink_proxy_started = False

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    # Add signal handlers for common shutdown signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: signal_handler())

    try:
        # Start MAVLink proxy
        mavlink_proxy.start()
        mavlink_proxy_started = True

        # Start server
        logger.info("Starting server. Press Ctrl+C to stop.")

        # Create task for server
        server_task = asyncio.create_task(server.start(mavlink_proxy))

        # Wait for either completion or shutdown signal
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel any remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error("Error running server: %s", e)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        server.close()
        if mavlink_proxy_started:
            mavlink_proxy.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
