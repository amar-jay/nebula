# #!/usr/bin/env python3
# import argparse
# import asyncio
# import logging
# import queue
# import socket
# import subprocess
# import threading
# import time
# import traceback
# from concurrent.futures import ThreadPoolExecutor
# from dataclasses import dataclass
# from typing import Any, Dict, Optional, Tuple

# import cv2
# import numpy as np
# import zmq
# import zmq.asyncio

# from src.controls.detection import yolo
# from src.controls.mavlink import ardupilot, gz, mission_types
# from src.mq.messages import ZMQTopics

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger("zmq-server")

# # RTSP streaming parameters
# RTSP_RAW_PORT = 8554
# RTSP_PROCESSED_PORT = 8555
# VIDEO_BITRATE = "2000k"
# VIDEO_FPS = 30
# VIDEO_GOP_SIZE = 60  # Keyframe interval


# @dataclass
# class FrameData:
#     """Data structure for frame processing"""

#     mode: str  # default is "UNKNOWN"
#     frame: np.ndarray
#     timestamp: float
#     drone_position: Tuple[float, float, float]
#     drone_attitude: Any
#     ground_level: float


# @dataclass
# class ProcessedResult:
#     """Result of frame processing"""

#     processed_frame: np.ndarray
#     gps_coordinates: Dict[str, Tuple[float, float]]
#     pixel_coordinates: Dict[str, Tuple[int, int]]
#     timestamp: float


# class RTSPServer:
#     """RTSP server using FFmpeg for streaming"""

#     def __init__(self, port: int, stream_name: str, width: int = 640, height: int = 480):
#         self.port = port
#         self.stream_name = stream_name
#         self.width = width
#         self.height = height
#         self.process = None
#         self.running = False

#     def start(self):
#         """Start the RTSP server"""
#         if self.running:
#             return

#         # FFmpeg command for RTSP streaming
#         ffmpeg_cmd = [
#             'ffmpeg',
#             '-f', 'rawvideo',
#             '-pix_fmt', 'bgr24',
#             '-s', f'{self.width}x{self.height}',
#             '-r', str(VIDEO_FPS),
#             '-i', '-',  # Input from stdin
#             '-c:v', 'libx264',
#             '-preset', 'ultrafast',
#             '-tune', 'zerolatency',
#             '-b:v', VIDEO_BITRATE,
#             '-g', str(VIDEO_GOP_SIZE),
#             '-keyint_min', str(VIDEO_GOP_SIZE),
#             '-sc_threshold', '0',
#             '-bf', '0',
#             '-refs', '1',
#             '-pix_fmt', 'yuv420p',
#             '-f', 'rtsp',
#             f'rtsp://localhost:{self.port}/{self.stream_name}'
#         ]

#         print("Starting RTSP server with command:", " ".join(ffmpeg_cmd))

#         try:
#             self.process = subprocess.Popen(
#                 ffmpeg_cmd,
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.DEVNULL,
#                 stderr=subprocess.DEVNULL,
#                 bufsize=0
#             )
#             self.running = True
#             logger.info(f"RTSP server started on rtsp://localhost:{self.port}/{self.stream_name}")
#         except Exception as e:
#             logger.error(f"Failed to start RTSP server: {e}")
#             raise

#     def send_frame(self, frame: np.ndarray):
#         """Send a frame to the RTSP stream"""
#         if not self.running or not self.process:
#             return False

#         try:
#             # Resize frame if necessary
#             if frame.shape[:2] != (self.height, self.width):
#                 frame = cv2.resize(frame, (self.width, self.height))

#             # Write frame to FFmpeg stdin
#             self.process.stdin.write(frame.tobytes())
#             return True
#         except Exception as e:
#             logger.warning(f"Failed to send frame to RTSP server: {e}")
#             return False

#     def stop(self):
#         """Stop the RTSP server"""
#         if not self.running:
#             return

#         self.running = False
#         if self.process:
#             try:
#                 self.process.stdin.close()
#                 self.process.terminate()
#                 self.process.wait(timeout=5)
#             except subprocess.TimeoutExpired:
#                 logger.warning("RTSP server process didn't terminate, killing...")
#                 self.process.kill()
#             except Exception as e:
#                 logger.error(f"Error stopping RTSP server: {e}")
#             finally:
#                 self.process = None

#         logger.info(f"RTSP server stopped (port {self.port})")


# class AsyncFrameProcessor:
#     """Asynchronous frame processor that doesn't block the main video loop"""

#     def __init__(self, tracker: yolo.YoloObjectTracker, object_classes, max_workers=2):
#         self.tracker = tracker
#         self.object_classes = object_classes
#         self.executor = ThreadPoolExecutor(max_workers=max_workers)
#         self.processing_queue = queue.Queue(
#             maxsize=3
#         )  # Small buffer to prevent memory issues
#         self.results_queue = queue.Queue(maxsize=10)
#         self.running = False
#         self.worker_thread = None

#     def start(self):
#         self.running = True
#         self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
#         self.worker_thread.start()

#     def stop(self):
#         self.running = False
#         if self.worker_thread:
#             self.worker_thread.join(timeout=2.0)
#         self.executor.shutdown(wait=True)

#     def submit_frame(self, frame_data: FrameData) -> bool:
#         """Submit a frame for processing. Returns False if queue is full."""
#         try:
#             self.processing_queue.put_nowait(frame_data)
#             return True
#         except queue.Full:
#             logger.warning("Processing queue is full, dropping oldest frame")
#             return False

#     def get_result(self) -> Optional[ProcessedResult]:
#         """Get the latest processed result, non-blocking."""
#         try:
#             return self.results_queue.get_nowait()
#         except queue.Empty:
#             return None

#     def _worker_loop(self):
#         """Worker thread that processes frames asynchronously"""
#         while self.running:
#             try:
#                 # Get frame data with timeout
#                 frame_data = self.processing_queue.get(timeout=0.1)

#                 # Process in thread pool to avoid blocking
#                 future = self.executor.submit(self._process_frame, frame_data)

#                 # Wait for result with timeout
#                 try:
#                     result = future.result(timeout=0.5)  # 500ms timeout for processing

#                     # Put result in results queue, drop oldest if full
#                     try:
#                         self.results_queue.put_nowait(result)
#                     except queue.Full:
#                         # Drop oldest result
#                         try:
#                             self.results_queue.get_nowait()
#                             self.results_queue.put_nowait(result)
#                         except queue.Empty:
#                             pass

#                 except Exception as e:
#                     logger.warning("Frame processing failed: %s", e)

#             except queue.Empty:
#                 continue
#             except Exception as e:
#                 logger.error("Error in frame processor worker: %s", e)
#                 time.sleep(0.1)

#     def _process_frame(self, frame_data: FrameData) -> ProcessedResult:
#         """Process a single frame"""
#         processed_frame, gps_coords, pixel_coords = self.tracker.process_frame(
#             frame=frame_data.frame,
#             drone_gps=frame_data.drone_position,
#             drone_attitude=frame_data.drone_attitude,
#             ground_level_masl=frame_data.ground_level,
#             object_classes=self.object_classes,
#         )

#         try:
#             processed_frame = self.tracker.write_on_frame(
#                 frame=processed_frame,
#                 curr_gps=frame_data.drone_position,
#                 gps_coords=gps_coords,
#                 pixel_coords=pixel_coords,
#                 mode=frame_data.mode,
#                 object_classes=self.object_classes,
#             )
#         except Exception:
#             logger.error(
#                 "Error writing on frame in _process_frame: %s", traceback.format_exc()
#             )
#             processed_frame = frame_data.frame.copy()

#         return ProcessedResult(
#             processed_frame=processed_frame,
#             gps_coordinates=gps_coords,
#             pixel_coordinates=pixel_coords,
#             timestamp=frame_data.timestamp,
#         )


# class MAVLinkProxy:
#     """Handles MAVLink connection and TCP proxy in a clean way"""

#     def __init__(
#         self, connection_string: str, tcp_host: str = "0.0.0.0", tcp_port: int = 16550
#     ):
#         self.connection_string = connection_string
#         self.tcp_host = tcp_host
#         self.tcp_port = tcp_port
#         self.connection = None
#         self.tcp_server = None
#         self.clients: list[socket.socket] = []
#         self.clients_lock = threading.Lock()
#         self.running = False

#     def start(self):
#         # Initialize MAVLink connection
#         try:
#             self.connection = ardupilot.ArdupilotConnection(
#                 connection_string=self.connection_string
#             )
#             logger.info("MAVLink connection established")
#         except ConnectionError:
#             logger.error("Failed to connect to MAVLink at %s", self.connection_string)
#             raise

#         # Set up TCP server
#         self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         self.tcp_server.bind((self.tcp_host, self.tcp_port))
#         self.tcp_server.listen(5)
#         logger.info("TCP server listening on %s:%d", self.tcp_host, self.tcp_port)

#         self.running = True

#         # Start background threads
#         threading.Thread(target=self._accept_clients, daemon=True).start()
#         threading.Thread(target=self._forward_serial_to_tcp, daemon=True).start()

#     def stop(self):
#         self.running = False
#         if self.tcp_server:
#             self.tcp_server.close()
#         if self.connection:
#             self.connection.close()
#         with self.clients_lock:
#             for client in self.clients:
#                 try:
#                     client.close()
#                 except Exception:
#                     logger.warning("Failed to close client socket")
#             self.clients.clear()

#     def get_drone_data(self) -> Tuple[Tuple[float, float, float, str], Any, float]:
#         """Get current drone position, attitude, and ground level"""
#         if not self.connection:
#             return None

#         try:
#             drone_position = self.connection.get_amsl_gps_location()
#             curr_position = (drone_position[0], drone_position[1], drone_position[2][1])
#             drone_attitude = self.connection.get_current_attitude()
#             ground_level = drone_position[2][1] - drone_position[2][0]
#             mode = self.connection.get_mode()
#             return curr_position, drone_attitude, ground_level, mode
#         except Exception as e:
#             logger.warning("Failed to get drone data: %s", e)
#             return None

#     def _accept_clients(self):
#         while self.running:
#             try:
#                 client_socket, client_address = self.tcp_server.accept()
#                 with self.clients_lock:
#                     self.clients.append(client_socket)
#                 logger.info("New client connected: %s", client_address)

#                 # Handle client in separate thread
#                 threading.Thread(
#                     target=self._handle_client,
#                     args=(client_socket, client_address),
#                     daemon=True,
#                 ).start()
#             except Exception as e:
#                 if self.running:
#                     logger.error("Error accepting client: %s", e)
#                     time.sleep(1)

#     def _handle_client(self, client_socket: socket.socket, client_address: tuple):
#         try:
#             while self.running:
#                 try:
#                     data = client_socket.recv(1024)
#                     if not data:
#                         break
#                     if self.connection:
#                         self.connection.master.write(data)
#                 except Exception as e:
#                     logger.error(f"Error handling client {client_address}: {e}")
#                     break
#         finally:
#             with self.clients_lock:
#                 if client_socket in self.clients:
#                     self.clients.remove(client_socket)
#             client_socket.close()
#             logger.info(f"Client disconnected: {client_address}")

#     def _forward_serial_to_tcp(self):
#         while self.running:
#             try:
#                 if not self.connection:
#                     time.sleep(0.1)
#                     continue

#                 msg = self.connection.master.recv_match(blocking=False)
#                 if msg is not None:
#                     msg_bytes = msg.get_msgbuf()

#                     with self.clients_lock:
#                         disconnected_clients: list[socket.socket] = []
#                         for client in self.clients:
#                             try:
#                                 client.send(msg_bytes)
#                             except Exception:
#                                 disconnected_clients.append(client)

#                         for client in disconnected_clients:
#                             self.clients.remove(client)
#                             try:
#                                 client.close()
#                             except:
#                                 pass
#                 else:
#                     time.sleep(0.001)  # Small sleep when no messages

#             except Exception as e:
#                 logger.error(f"Error in serial to TCP forwarding: {e}")
#                 time.sleep(0.1)


# class ZMQServer:
#     """ZMQ server that publishes video via RTSP and handles control commands"""

#     def __init__(
#         self,
#         control_port: int = 5556,
#         video_source: int = 0,
#         is_simulation: bool = False,
#         rtsp_raw_port: int = RTSP_RAW_PORT,
#         rtsp_processed_port: int = RTSP_PROCESSED_PORT,
#     ):
#         self.control_port = control_port
#         self.video_source = video_source
#         self.is_simulation = is_simulation
#         self.rtsp_raw_port = rtsp_raw_port
#         self.rtsp_processed_port = rtsp_processed_port

#         # ZMQ Context
#         self.context = zmq.asyncio.Context()

#         # Control socket only (video now via RTSP)
#         self.control_socket = None

#         # Video capture
#         self.cap = None

#         # RTSP servers
#         self.raw_rtsp_server = None
#         self.processed_rtsp_server = None

#         # State
#         self.hook_state = "dropped"
#         self.running = False

#         # Latest processed results
#         self.latest_gps_coordinates = {}
#         self.latest_pixel_coordinates = {}

#         # Frame processor
#         self.frame_processor = None

#         # Object classes
#         self.object_classes = ["helipad", "tank" if is_simulation else "real_tank"]

#         # Initialize tracker
#         self._initialize_tracker()

#     def _initialize_tracker(self):
#         """Initialize YOLO tracker with proper camera intrinsics"""
#         if self.is_simulation:
#             camera_intrinsics = gz.get_camera_intrinsics(
#                 model_name="iris_with_stationary_gimbal",
#                 camera_link="tilt_link",
#                 world="delivery_runway",
#             )
#         else:
#             camera_intrinsics = mission_types.get_camera_intrinsics()

#         if camera_intrinsics is None:
#             logger.error("Failed to get camera intrinsics")
#             raise RuntimeError("Failed to get camera intrinsics")

#         camera_intrinsics = camera_intrinsics.get("camera_intrinsics", None)
#         if camera_intrinsics is None:
#             logger.error("Camera intrinsics not found in response")
#             raise RuntimeError("Camera intrinsics not found")

#         self.tracker = yolo.YoloObjectTracker(
#             K=camera_intrinsics,
#             model_path="src/controls/detection/sim.pt"
#             if self.is_simulation
#             else "src/controls/detection/main.pt",
#         )

#         # Initialize frame processor
#         self.frame_processor = AsyncFrameProcessor(
#             tracker=self.tracker, object_classes=self.object_classes, max_workers=2
#         )

#     def _initialize_video_capture(self) -> bool:
#         """Initialize video capture"""
#         try:
#             if self.is_simulation:
#                 self.cap = gz.GazeboVideoCapture(camera_port=5600)
#             else:
#                 self.cap = cv2.VideoCapture(self.video_source)

#             if not self.cap.isOpened():
#                 logger.error(f"Failed to open video source {self.video_source}")
#                 return False

#             logger.info("Video capture initialized successfully")
#             return True

#         except Exception as e:
#             logger.error("Error initializing video capture: %s", e)
#             return False

#     def _initialize_rtsp_servers(self) -> bool:
#         """Initialize RTSP servers"""
#         try:
#             # Get frame dimensions
#             if not self._initialize_video_capture():
#                 return False

#             ret, test_frame = self.cap.read()
#             if not ret:
#                 logger.error("Failed to read test frame for RTSP server initialization")
#                 return False

#             height, width = test_frame.shape[:2]
#             logger.info(f"Video dimensions: {width}x{height}")

#             # Initialize RTSP servers
#             self.raw_rtsp_server = RTSPServer(
#                 port=self.rtsp_raw_port,
#                 stream_name="raw",
#                 width=width,
#                 height=height
#             )

#             self.processed_rtsp_server = RTSPServer(
#                 port=self.rtsp_processed_port,
#                 stream_name="processed",
#                 width=width,
#                 height=height
#             )

#             # Start RTSP servers
#             self.raw_rtsp_server.start()
#             self.processed_rtsp_server.start()

#             logger.info(f"RTSP streams available at:")
#             logger.info(f"  Raw video: rtsp://localhost:{self.rtsp_raw_port}/raw")
#             logger.info(f"  Processed video: rtsp://localhost:{self.rtsp_processed_port}/processed")

#             return True

#         except Exception as e:
#             logger.error(f"Error initializing RTSP servers: {e}")
#             return False

#     async def _video_publisher_loop(self, mavlink_proxy: MAVLinkProxy):
#         """Main video publishing loop via RTSP"""
#         if not self._initialize_rtsp_servers():
#             return

#         logger.info("RTSP video publishing started")

#         frame_count = 0
#         fps_timer = time.time()
#         process_every_n_frames = 3  # Process every 3rd frame for object detection

#         while self.running:
#             try:
#                 ret, frame = self.cap.read()
#                 if not ret:
#                     logger.warning("Failed to capture frame")
#                     await asyncio.sleep(0.1)
#                     continue

#                 # Always send raw frame to RTSP
#                 self.raw_rtsp_server.send_frame(frame)

#                 # Submit frame for processing (non-blocking)
#                 if frame_count % process_every_n_frames == 0:
#                     data = mavlink_proxy.get_drone_data()
#                     if data is None:
#                         logger.warning(
#                             "No drone data available, skipping frame processing"
#                         )
#                         await asyncio.sleep(0.033)  # ~30 FPS
#                         continue
#                     (
#                         drone_pos,
#                         drone_att,
#                         ground_level,
#                         mode,
#                     ) = data

#                     frame_data = FrameData(
#                         frame=frame.copy(),
#                         timestamp=time.time(),
#                         drone_position=drone_pos,
#                         drone_attitude=drone_att,
#                         ground_level=ground_level,
#                         mode=mode,
#                     )

#                     # Submit for processing (non-blocking)
#                     if not self.frame_processor.submit_frame(frame_data):
#                         logger.debug("Frame processor queue full, skipping frame")

#                 # Check for processed results
#                 result = self.frame_processor.get_result()
#                 if result:
#                     # Update latest coordinates
#                     if result.gps_coordinates is not None:
#                         self.latest_gps_coordinates = result.gps_coordinates
#                     if result.pixel_coordinates is not None:
#                         self.latest_pixel_coordinates = result.pixel_coordinates

#                     # Send processed frame to RTSP
#                     self.processed_rtsp_server.send_frame(result.processed_frame)

#                 frame_count += 1

#                 # FPS logging
#                 if time.time() - fps_timer > 5:
#                     fps = frame_count / 5
#                     logger.info(f"Publishing video at {fps:.1f} FPS")
#                     frame_count = 0
#                     fps_timer = time.time()

#                 # Frame rate control (~30 FPS)
#                 await asyncio.sleep(0.033)

#             except Exception:
#                 logger.error("Error in video loop:\n%s", traceback.format_exc())
#                 await asyncio.sleep(0.1)

#         # Cleanup
#         if self.cap:
#             self.cap.release()
#         logger.info("RTSP video publishing stopped")

#     async def _control_receiver_loop(self):
#         """Control command receiver loop"""
#         logger.info("Control receiver started")

#         while self.running:
#             try:
#                 # Check for messages with timeout
#                 if await self.control_socket.poll(timeout=100):
#                     message = await self.control_socket.recv_string()
#                     response = self._handle_command(message)
#                     await self.control_socket.send_string(response)
#                     if "NACK" not in message:
#                         logger.info(f"Command: {message} -> Response: {response}")

#             except Exception as e:
#                 logger.error(f"Error in control receiver: {e}")
#                 await asyncio.sleep(0.1)

#     def _handle_command(self, command: str) -> str:
#         """Handle control commands"""
#         command = command.strip()

#         if command == ZMQTopics.DROP_LOAD.name:
#             return "ACK: Load dropped"
#         elif command == ZMQTopics.PICK_LOAD.name:
#             return "ACK: Load picked"
#         elif command == ZMQTopics.RAISE_HOOK.name:
#             if self.hook_state == "raised":
#                 return "ACK: Hook already raised"
#             else:
#                 self.hook_state = "raised"
#                 return "ACK: Hook raised"
#         elif command == ZMQTopics.DROP_HOOK.name:
#             if self.hook_state == "dropped":
#                 return "ACK: Hook already dropped"
#             else:
#                 self.hook_state = "dropped"
#                 return "ACK: Hook dropped"
#         elif command == ZMQTopics.STATUS.name:
#             return f"ACK: Hook is {self.hook_state}"
#         elif command == ZMQTopics.HELIPAD_GPS.name:
#             if self.latest_gps_coordinates and "helipad" in self.latest_gps_coordinates:
#                 coords = self.latest_gps_coordinates["helipad"]
#                 return f"ACK>{coords[0]},{coords[1]}"
#             else:
#                 return "NACK: No GPS data available"
#         elif command == ZMQTopics.TANK_GPS.name:
#             tank_key = "tank" if self.is_simulation else "real_tank"
#             if self.latest_gps_coordinates and tank_key in self.latest_gps_coordinates:
#                 coords = self.latest_gps_coordinates[tank_key]
#                 return f"ACK>{coords[0]},{coords[1]}"
#             else:
#                 return "NACK: No GPS data available"
#         elif command == "RTSP_INFO":
#             return f"ACK>raw:rtsp://localhost:{self.rtsp_raw_port}/raw,processed:rtsp://localhost:{self.rtsp_processed_port}/processed"
#         else:
#             logger.error("Unknown command: %s", command)
#             return "NACK: Unknown command"

#     async def start(self, mavlink_proxy: MAVLinkProxy):
#         """Start the server"""
#         if self.running:
#             logger.warning("Server is already running")
#             return

#         # Initialize ZMQ control socket only
#         self.control_socket = self.context.socket(zmq.REP)
#         self.control_socket.bind(f"tcp://*:{self.control_port}")

#         # Start frame processor
#         self.frame_processor.start()

#         self.running = True
#         logger.info("Server started")

#         # Run both loops concurrently
#         await asyncio.gather(
#             self._video_publisher_loop(mavlink_proxy), self._control_receiver_loop()
#         )

#     def stop(self):
#         """Stop the server"""
#         logger.info("Stopping server...")
#         self.running = False

#         # Stop frame processor
#         if self.frame_processor:
#             self.frame_processor.stop()

#         # Stop RTSP servers
#         if self.raw_rtsp_server:
#             self.raw_rtsp_server.stop()
#         if self.processed_rtsp_server:
#             self.processed_rtsp_server.stop()

#         # Close ZMQ socket
#         if self.control_socket:
#             self.control_socket.close()

#         # Terminate context
#         self.context.term()

#         logger.info("Server stopped")


# async def main():
#     parser = argparse.ArgumentParser(description="ZMQ Control Server with RTSP Video")
#     parser.add_argument(
#         "--is-simulation", action="store_true", help="Run in simulation mode"
#     )
#     parser.add_argument(
#         "--control-port", type=int, default=5556, help="Port for control commands"
#     )
#     parser.add_argument(
#         "--video-source", default=0, help="Video source (device ID or file path)"
#     )
#     parser.add_argument(
#         "--rtsp-raw-port", type=int, default=RTSP_RAW_PORT, help="RTSP port for raw video"
#     )
#     parser.add_argument(
#         "--rtsp-processed-port", type=int, default=RTSP_PROCESSED_PORT, help="RTSP port for processed video"
#     )

#     args = parser.parse_args()

#     # Convert video_source to int if it's a number
#     try:
#         args.video_source = int(args.video_source)
#     except ValueError:
#         pass

#     # Check if FFmpeg is available
#     try:
#         subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
#         logger.info("FFmpeg found - RTSP streaming enabled")
#     except (subprocess.CalledProcessError, FileNotFoundError):
#         logger.error("FFmpeg not found! Please install FFmpeg for RTSP streaming")
#         logger.error("On Ubuntu: sudo apt install ffmpeg")
#         logger.error("On macOS: brew install ffmpeg")
#         return

#     # Initialize MAVLink proxy
#     connection_string = (
#         "udp:127.0.0.1:14550"  # if args.is_simulation else "/dev/ttyUSB0"
#     )
#     mavlink_proxy = MAVLinkProxy(connection_string)

#     # Enable video streaming for simulation
#     if args.is_simulation:
#         logger.info("Enabling video streaming for simulation")
#         done = gz.enable_streaming(
#             world="delivery_runway",
#             model_name="iris_with_stationary_gimbal",
#             camera_link="tilt_link",
#         )
#         if not done:
#             logger.error("Failed to enable streaming")
#             return

#     # Initialize server
#     server = ZMQServer(
#         control_port=args.control_port,
#         video_source=args.video_source,
#         is_simulation=args.is_simulation,
#         rtsp_raw_port=args.rtsp_raw_port,
#         rtsp_processed_port=args.rtsp_processed_port,
#     )

#     try:
#         # Start MAVLink proxy
#         mavlink_proxy.start()

#         # Start server
#         logger.info("Starting server. Press Ctrl+C to stop.")
#         logger.info(f"Control commands available on port {args.control_port}")
#         logger.info(f"RTSP streams will be available on ports {args.rtsp_raw_port} and {args.rtsp_processed_port}")
#         await server.start(mavlink_proxy)

#     except Exception as e:
#         logger.exception(f"Unexpected error: {e}")
#     finally:
#         # Cleanup
#         logger.info("Shutting down...")
#         server.stop()
#         mavlink_proxy.stop()


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\n[INFO] Server shutdown by Ctrl+C")
