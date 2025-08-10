#!/usr/bin/env python3
"""
Real-time USB Camera Streaming System
Captures frames from USB camera and streams to named pipe for ffplay consumption
"""

import os
import subprocess
import sys

import numpy as np
import cv2


class VideoWriter:
    def __init__(self, source: str, width: int, height: int, fps: int):
        self.pipe_path = source
        self.width = width
        self.height = height
        self.fps = fps
        self._running = False
        pass

    def write(self, frame: np.ndarray) -> bool:
        pass

    def close(self):
        pass


class TSVideoWriter(VideoWriter):
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

        if self._setup_h264_encoder():
            print("H.264 encoder setup successfully.")
        else:
            print("Failed to set up H.264 encoder.")

        self._recreate_pipe()
        self._running = True

    def _setup_h264_encoder(self) -> bool:
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
        return self._setup_h264_encoder()

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
                
                # Explicitly delete frame data to free memory
                del frame_data

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

class RTSPVideoWriter:
    def __init__(self, source: str, width: int, height: int, fps: int):
        """
        RTSP Video Writer using FFmpeg subprocess.
        :param source: RTSP URL (e.g., 'rtsp://localhost:8554/mystream')
        :param width: Frame width in pixels
        :param height: Frame height in pixels
        :param fps: Frames per second
        """
        self.pipe_path = source
        self.width = width
        self.height = height
        self.fps = fps
        self._running = True

        # Start ffmpeg process for RTSP streaming
        self.process = subprocess.Popen([
            'ffmpeg',
            '-y',  # Overwrite output
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{self.width}x{self.height}',
            '-r', str(self.fps),
            '-i', '-',  # Read frames from stdin
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-f', 'rtsp',
            self.pipe_path
        ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def write(self, frame: np.ndarray) -> bool:
        """
        Writes a frame to the RTSP stream.
        :param frame: NumPy array (BGR)
        :return: True if written successfully, False otherwise
        """
        if not self._running or frame is None:
            return False
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        try:
            self.process.stdin.write(frame.tobytes())
            self.process.stdin.flush()  # Ensure data is sent immediately
            return True
        except (BrokenPipeError, IOError):
            self._running = False
            return False

    def close(self):
        """Closes the RTSP stream."""
        if self._running:
            self._running = False
            try:
                self.process.stdin.close()
                self.process.wait()
            except Exception:
                pass


def signal_handler(*_):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal...")
    streamer = signal_handler.streamer
    if streamer:
        streamer.close()
    sys.exit(0)


signal_handler.streamer = None
