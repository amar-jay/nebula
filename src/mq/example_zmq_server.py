#!/usr/bin/env python3
import cv2
import zmq
import time
import numpy as np
import threading
import argparse
import logging
from typing import Tuple
import socket
import threading
import time
from pymavlink import mavutil
from .messages import ZMQTopics
from src.controls.mavlink import gz

logging.basicConfig(
	level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zmq-video-server")


# Configuration
serial_port = "/dev/ttyACM0"  # Change to your serial port
baud_rate = 57600  # Change to your baud rate
tcp_host = "0.0.0.0"  # Listen on all interfaces
tcp_port = 16550  # Standard MAVLink port

# List to keep track of client connections
clients = []
clients_lock = threading.Lock()

# Connect to the drone via serial
print(f"Connecting to serial port {serial_port}...")
try:
	serial_connection = mavutil.mavlink_connection(
		# serial_port,
		# baud=baud_rate,
		"udp:127.0.0.1:14550",
		source_system=255,  # Using 255 for GCS
	)
except Exception as e:
	print(f"Error connecting to serial port")
	exit(1)
print("Serial connection established")


# Set up TCP server
tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp_server.bind((tcp_host, tcp_port))
tcp_server.listen(5)  # Allow up to 5 connections
print(f"TCP server listening on {tcp_host}:{tcp_port}")


def handle_client(client_socket, client_address):
	print(f"New client connected: {client_address}")

	try:
		while True:
			# Read from TCP client
			try:
				data = client_socket.recv(1024)
				if not data:
					break  # Client disconnected

				# Forward from TCP client to serial
				serial_connection.write(data)
			except Exception as e:
				print(f"Error reading from client {client_address}: {e}")
				break
	finally:
		with clients_lock:
			clients.remove(client_socket)
		client_socket.close()
		print(f"Client disconnected: {client_address}")


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
			print(f"Error accepting client: {e}")
			time.sleep(1)  # Avoid CPU spinning on error


def forward_from_serial_to_tcp():
	while True:
		try:
			# Wait for a message from the serial connection
			msg = serial_connection.recv_match(blocking=True)
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
			print(f"Error in serial to TCP forwarding: {e}")
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
		self.is_simulation = is_simulation
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

		# Enable video streaming for simulation
		if self.is_simulation:
			print("Enabling video streaming")
			done = self.master_connection.enable_streaming()
			print("Enabling streaming")
			if not done:
				print("❌ Failed to enable streaming.")
				return False
		logger.info(
			f"Server initialized with video port {video_port} and control port {control_port}"
		)

	def start_capture(self) -> bool:
		"""Start the video capture"""
		try:
			if self.is_simulation:
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
			processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
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

		else:
			print(f"Unknown command: {command}")
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
	parser = argparse.ArgumentParser(
		description="ZMQ Video Server with Control Interface"
	)
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
		serial_connection.close()
		with clients_lock:
			for client in clients:
				try:
					client.close()
				except:
					pass


if __name__ == "__main__":
	main()
