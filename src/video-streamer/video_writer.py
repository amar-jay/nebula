#!/usr/bin/env python3
"""
Real-time USB Camera Streaming System
Captures frames from USB camera and streams to named pipe for ffplay consumption
"""

import argparse
import os
import signal
import subprocess
import sys
import time

import cv2
import numpy as np


class VideoWriter:
	def __init__(self, source: str, width: int, height: int, fps: int):
		"""
		Initialize the VideoWriter

		Args:
		    filename: Output file name
		    width: Frame width
		    height: Frame height
		    fps: Frames per second
		"""
		self.pipe_path = source
		self.width = width
		self.height = height
		self.fps = fps
		self.writer = None
		self.ffmpeg_process = None
		self._running = False

		if self.setup_h264_encoder():
			print("H.264 encoder setup successfully.")
		else:
			print("Failed to set up H.264 encoder.")

		self._recreate_pipe()
		self._running = True

	def setup_h264_encoder(self) -> bool:
		"""Setup ffmpeg H.264 encoder process"""
		try:
			# ffmpeg command for H.264 encoding with low latency
			ffmpeg_cmd = [
				"ffmpeg",
				"-y",  # Overwrite output
				"-f",
				"rawvideo",  # Input format
				"-vcodec",
				"rawvideo",
				"-s",
				f"{self.width}x{self.height}",  # Input size
				"-pix_fmt",
				"bgr24",  # OpenCV uses BGR format
				"-r",
				str(self.fps),  # Input framerate
				"-i",
				"-",  # Read from stdin
				"-c:v",
				"libx264",  # H.264 encoder
				"-preset",
				"ultrafast",  # Fastest encoding preset
				"-tune",
				"zerolatency",  # Optimize for low latency
				"-crf",
				"23",  # Quality (lower = better quality, 18-28 is reasonable)
				"-maxrate",
				"2M",  # Max bitrate
				"-bufsize",
				"4M",  # Buffer size
				"-g",
				str(self.fps),  # GOP size (keyframe interval)
				"-keyint_min",
				str(self.fps),  # Minimum GOP size
				"-f",
				"mpegts",  # Transport stream format
				self.pipe_path,  # Output to named pipe
			]

			print("Starting H.264 encoder...")
			self.ffmpeg_process = subprocess.Popen(
				ffmpeg_cmd,
				stdin=subprocess.PIPE,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
			)

			return True

		except Exception as e:
			print(f"Error setting up H.264 encoder: {e}")
			return False

	def restart_h264_encoder(self) -> bool:
		"""Restart the H.264 encoder process for live streaming"""
		print("Restarting H.264 encoder for live stream (clearing pipe buffer)...")

		# Clean up existing process if any
		if self.ffmpeg_process:
			try:
				if self.ffmpeg_process.stdin:
					self.ffmpeg_process.stdin.close()
				self.ffmpeg_process.terminate()
				self.ffmpeg_process.wait(timeout=2)
			except:
				pass
			self.ffmpeg_process = None

		# For live streaming: recreate the pipe to clear any buffered data
		self._recreate_pipe()

		# Restart the encoder
		return self.setup_h264_encoder()

	def _recreate_pipe(self):
		"""Recreate the named pipe to clear buffered data for live streaming"""
		try:
			# Remove existing pipe
			if os.path.exists(self.pipe_path):
				os.unlink(self.pipe_path)

			# Create fresh pipe
			os.mkfifo(self.pipe_path)
			print("Live stream pipe recreated to clear buffer")
		except Exception as e:
			print(f"Warning: Could not recreate pipe: {e}")

	def write(self, frame: np.ndarray) -> bool:
		try:
			# Check if encoder needs to be started or restarted
			if not self.ffmpeg_process or self.ffmpeg_process.poll() is not None:
				print("Starting/restarting encoder for live stream...")
				if not self.restart_h264_encoder():
					print("Failed to restart H.264 encoder")
					return False

			# Send raw frame data to ffmpeg
			if self.ffmpeg_process and self.ffmpeg_process.stdin:
				frame_data = frame.tobytes()

				self.ffmpeg_process.stdin.write(frame_data)
				self.ffmpeg_process.stdin.flush()

				return True

		except BrokenPipeError:
			print(
				"Live stream client disconnected - will restart encoder to clear buffer"
			)
			# For live streaming, we restart to clear the pipe buffer
			self.ffmpeg_process = None
			return False
		except OSError as e:
			print(f"Live stream write error: {e} - will restart encoder")
			# For live streaming, restart to maintain continuity
			self.ffmpeg_process = None
			return False

	def close(self):
		"""Stop streaming and cleanup resources"""

		# Cleanup ffmpeg process
		if self.ffmpeg_process:
			try:
				if self.ffmpeg_process.stdin:
					self.ffmpeg_process.stdin.close()
				self.ffmpeg_process.terminate()
				self.ffmpeg_process.wait(timeout=5)
			except subprocess.TimeoutExpired:
				self.ffmpeg_process.kill()
			except Exception:
				pass

		# Cleanup pipe
		if os.path.exists(self.pipe_path):
			os.unlink(self.pipe_path)
		self._running = False


def signal_handler(*_):
	"""Handle Ctrl+C gracefully"""
	print("\nReceived interrupt signal...")
	streamer = signal_handler.streamer
	if streamer:
		streamer.close()
	sys.exit(0)


def main():
	parser = argparse.ArgumentParser(description="USB Camera Streaming System")
	parser.add_argument(
		"--source", "-c", type=int, default=0, help="Camera device ID (default: 0)"
	)
	parser.add_argument(
		"--width", "-w", type=int, default=0, help="Frame width (default: 640)"
	)
	parser.add_argument(
		"--height", "-H", type=int, default=0, help="Frame height (default: 480)"
	)
	parser.add_argument(
		"--fps", "-f", type=int, default=30, help="Target FPS (default: 30)"
	)
	parser.add_argument(
		"--pipe",
		"-p",
		type=str,
		default="/tmp/camera_stream",
		help="Named pipe path (default: /tmp/camera_stream)",
	)

	args = parser.parse_args()

	cap = cv2.VideoCapture(args.source)
	if not cap.isOpened():
		print(f"Error: Could not open camera {args.source}")
		sys.exit(1)

	# Set camera properties
	width = args.width if args.width > 0 else int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
	height = args.height if args.height > 0 else int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
	fps = (
		args.fps if args.fps > 0 else 30
	)  # by default OpenCv transmits at 10 fps, so we set it to 30
	streamer = VideoWriter(
		source=args.pipe,
		width=width,
		height=height,
		fps=fps,
	)
	signal_handler.streamer = streamer

	# Set up signal handler for graceful shutdown
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	print("=== USB Camera Streaming System ===")
	print(f"Camera: {args.source}")
	print(f"Resolution: {width}x{height}")
	print(f"Target FPS: {fps}")
	print(f"Pipe: {args.pipe}")
	print("Press Ctrl+C to stop\n")

	print("\nTo view H.264 stream, run in another terminal:")
	print(f"ffplay -f mpegts -fflags nobuffer -flags low_delay {args.pipe}")
	print("# or with VLC:")
	print(f"vlc {args.pipe}")
	print(
		"\nNote: Live stream will restart encoder when clients connect/disconnect to ensure current feed."
	)

	failed_writes = 0
	max_consecutive_failures = 10  # Allow some failures before extra logging

	while streamer._running:
		ret, frame = cap.read()
		if not ret:
			print("Error: Could not read frame from camera")
			break

		# Resize frame if necessary
		if frame.shape[1] != width or frame.shape[0] != height:
			frame = cv2.resize(frame, (width, height))
		# Convert frame to BGR format if needed
		if frame.shape[2] != 3:
			print("Error: Frame is not in BGR format")
			break

		# set frame to gray
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		# Convert frame to BGR format
		frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

		# Write frame to pipe (single write for live streaming)
		if not streamer.write(frame):
			failed_writes += 1
			if failed_writes <= max_consecutive_failures or failed_writes % 50 == 0:
				print(
					f"Live stream write failed (attempt {failed_writes}) - continuing..."
				)
			# Continue to next frame for live streaming
			continue
		else:
			# Reset failure counter on successful write
			if failed_writes > 0:
				print(f"Live stream recovered after {failed_writes} failed attempts")
				failed_writes = 0

		# break on q
		if cv2.waitKey(1) & 0xFF == ord("q"):
			break

	cap.release()
	streamer.close()
	print("Streaming stopped. Cleaning up resources...")


if __name__ == "__main__":
	main()
