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

# Global variable for signal handler
streamer = None


class CameraStreamer:
	def __init__(
		self,
		pipe_path: str,
		camera_id: int = 0,
		width: int = 640,
		height: int = 480,
		fps: int = 30,
	):
		"""
		Initialize the camera streamer

		Args:
		    camera_id: USB camera device ID (usually 0)
		    width: Frame width
		    height: Frame height
		    fps: Target frames per second
		    pipe_path: Named pipe path for streaming
		"""
		self.camera_id = camera_id
		self.width = width
		self.height = height
		self.fps = fps
		self.pipe_path = pipe_path

		self.cap = None
		self.pipe_fd = None
		self.running = False
		self.ffmpeg_process = None

		# Performance monitoring
		self.frame_count = 0
		self.start_time = None

		self.bytes_written = 0
		self.last_bandwidth_time = None
		self.bandwidth_samples = []

	def setup_camera(self) -> bool:
		"""Initialize and configure the USB camera"""
		print(f"Initializing camera {self.camera_id}...")

		self.cap = cv2.VideoCapture(self.camera_id)
		if not self.cap.isOpened():
			print(f"Error: Could not open camera {self.camera_id}")
			return False

		# Configure camera properties
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
		self.cap.set(cv2.CAP_PROP_FPS, self.fps)

		# Reduce buffer size to minimize latency
		self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

		# Verify settings
		actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
		actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
		actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

		print(f"Camera configured: {actual_width}x{actual_height} @ {actual_fps} FPS")
		return True

	def calculate_bandwidth_metrics(
		self, frame_size: int, current_time: float
	) -> tuple:
		"""Calculate current and average bandwidth metrics"""
		self.bytes_written += frame_size

		# Calculate instantaneous bandwidth (last 1 second)
		if self.last_bandwidth_time is None:
			self.last_bandwidth_time = current_time
			instantaneous_bandwidth = 0
		else:
			time_diff = current_time - self.last_bandwidth_time
			if time_diff >= 1.0:  # Calculate every second
				instantaneous_bandwidth = frame_size / time_diff  # bytes per second
				self.bandwidth_samples.append(instantaneous_bandwidth)

				# Keep only last 10 samples for moving average
				if len(self.bandwidth_samples) > 10:
					self.bandwidth_samples.pop(0)

				self.last_bandwidth_time = current_time
			else:
				instantaneous_bandwidth = (
					self.bandwidth_samples[-1] if self.bandwidth_samples else 0
				)

		# Calculate average bandwidth since start
		elapsed = current_time - self.start_time if self.start_time else 1
		average_bandwidth = self.bytes_written / elapsed if elapsed > 0 else 0

		return instantaneous_bandwidth, average_bandwidth

	def format_bandwidth(self, bytes_per_second: float) -> str:
		"""Format bandwidth in human-readable units"""
		if bytes_per_second < 1024:
			return f"{bytes_per_second:.1f} B/s"
		elif bytes_per_second < 1024 * 1024:
			return f"{bytes_per_second / 1024:.1f} KB/s"
		else:
			return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"

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

	def setup_pipe(self) -> bool:
		"""Create named pipe for H.264 stream output"""
		try:
			# Remove existing pipe if it exists
			if os.path.exists(self.pipe_path):
				os.unlink(self.pipe_path)

			# Create named pipe
			os.mkfifo(self.pipe_path)
			print(f"Created named pipe: {self.pipe_path}")

			return True

		except OSError as e:
			print(f"Error setting up pipe: {e}")
			return False

	def start_streaming(self) -> bool:
		"""Start the H.264 streaming process"""
		if not self.setup_camera():
			return False

		if not self.setup_pipe():
			return False

		if not self.setup_h264_encoder():
			return False

		print("Starting H.264 streaming...")
		self.running = True
		self.start_time = time.time()

		frame_interval = 1.0 / self.fps
		last_frame_time = 0
		last_status_time = time.time()
		dropped_frames = 0

		try:
			while self.running:
				current_time = time.time()

				# Read frame from camera
				ret, frame = self.cap.read()
				if not ret:
					print("Warning: Failed to capture frame")
					time.sleep(0.01)
					continue

				# Check timing for frame rate control
				time_since_last = current_time - last_frame_time
				if time_since_last < frame_interval:
					# Skip this frame to maintain target FPS
					dropped_frames += 1
					continue

				try:
					# Send raw frame data to ffmpeg
					if self.ffmpeg_process and self.ffmpeg_process.stdin:
						frame_data = frame.tobytes()
						frame_size = len(frame_data)

						self.ffmpeg_process.stdin.write(frame_data)
						self.ffmpeg_process.stdin.flush()

						self.frame_count += 1
						last_frame_time = current_time

				except BrokenPipeError:
					print("ffmpeg process ended")
					break
				except OSError as e:
					print(f"Error writing to ffmpeg: {e}")
					break

				# Print status every 5 seconds
				if current_time - last_status_time >= 5.0:
					elapsed = current_time - self.start_time
					avg_fps = self.frame_count / elapsed if elapsed > 0 else 0
					drop_rate = (
						(dropped_frames / (self.frame_count + dropped_frames)) * 100
						if (self.frame_count + dropped_frames) > 0
						else 0
					)

					# Get latest bandwidth metrics
					_, avg_bandwidth = self.calculate_bandwidth_metrics(0, current_time)
					inst_bandwidth = (
						self.bandwidth_samples[-1] if self.bandwidth_samples else 0
					)

					print(
						f"Status: {avg_fps:.1f} FPS, Frames: {self.frame_count}, Dropped: {dropped_frames} ({drop_rate:.1f}%)"
					)
					print(
						f"        Bandwidth - Current: {self.format_bandwidth(inst_bandwidth)}, Average: {self.format_bandwidth(avg_bandwidth)}"
					)
					print(
						f"        Total data sent: {self.format_bandwidth(self.bytes_written).replace('/s', '')}"
					)
					last_status_time = current_time

		except KeyboardInterrupt:
			pass

		return True

	def stop_streaming(self):
		"""Stop streaming and cleanup resources"""
		print("\nStopping stream...")
		self.running = False

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

		# Cleanup camera
		if self.cap:
			self.cap.release()

		# Cleanup pipe
		if os.path.exists(self.pipe_path):
			os.unlink(self.pipe_path)

		# Print statistics
		if self.start_time:
			duration = time.time() - self.start_time
			avg_fps = self.frame_count / duration if duration > 0 else 0
			avg_bandwidth = self.bytes_written / duration if duration > 0 else 0

			print("Streaming statistics:")
			print(f"  Duration: {duration:.1f} seconds")
			print(f"  Frames streamed: {self.frame_count}")
			print(f"  Average FPS: {avg_fps:.1f}")
			print(
				f"  Total data transmitted: {self.format_bandwidth(self.bytes_written).replace('/s', '')}"
			)
			print(f"  Average bandwidth: {self.format_bandwidth(avg_bandwidth)}")
			print(
				f"  Compression ratio: {(self.frame_count * self.width * self.height * 3) / self.bytes_written:.1f}:1"
				if self.bytes_written > 0
				else "  Compression ratio: N/A"
			)


def signal_handler(_):
	"""Handle Ctrl+C gracefully"""
	print("\nReceived interrupt signal...")
	if streamer:
		streamer.stop_streaming()
	sys.exit(0)


def main():
	parser = argparse.ArgumentParser(description="USB Camera Streaming System")
	parser.add_argument(
		"--camera", "-c", type=int, default=0, help="Camera device ID (default: 0)"
	)
	parser.add_argument(
		"--width", "-w", type=int, default=640, help="Frame width (default: 640)"
	)
	parser.add_argument(
		"--height", "-H", type=int, default=480, help="Frame height (default: 480)"
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

	global streamer
	streamer = CameraStreamer(
		camera_id=args.camera,
		width=args.width,
		height=args.height,
		fps=args.fps,
		pipe_path=args.pipe,
	)

	# Set up signal handler for graceful shutdown
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	print("=== USB Camera Streaming System ===")
	print(f"Camera: {args.camera}")
	print(f"Resolution: {args.width}x{args.height}")
	print(f"Target FPS: {args.fps}")
	print(f"Pipe: {args.pipe}")
	print("Press Ctrl+C to stop\n")

	if streamer.start_streaming():
		print("\nTo view H.264 stream, run in another terminal:")
		print(f"ffplay -f mpegts -fflags nobuffer -flags low_delay {args.pipe}")
		print("# or with VLC:")
		print(f"vlc {args.pipe}")
	else:
		print("Failed to start streaming")
		sys.exit(1)


if __name__ == "__main__":
	main()
