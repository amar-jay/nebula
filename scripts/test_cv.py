#!/usr/bin/env python3
import argparse
import os
import platform
import sys

# Suppress OpenCV warnings
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import cv2
import numpy as np


# Optional: colored output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"


# Define backend mapping once
BACKENDS = {
    "ANY": cv2.CAP_ANY,
    "V4L": cv2.CAP_V4L,
    "V4L2": cv2.CAP_V4L2,
    "GSTREAMER": cv2.CAP_GSTREAMER,
    "FFMPEG": cv2.CAP_FFMPEG,
}


def print_info():
    print("\n===== OpenCV & System Info =====")
    print(
        f"OpenCV: {cv2.__version__} | Python: {platform.python_version()} | NumPy: {np.__version__}"
    )


def check_backends():
    """Check availability of backends and return results."""
    print("\n----- Backend Availability -----")
    results = {}
    for name, backend in BACKENDS.items():
        try:
            cap = cv2.VideoCapture(0, backend)
            available = cap.isOpened()
            cap.release()
        except Exception:
            available = False
        results[name] = available
        status = (
            f"{Colors.GREEN}✓ Available{Colors.RESET}"
            if available
            else f"{Colors.RED}✗ Not available{Colors.RESET}"
        )
        print(f"{name:<10}: {status}")
    return results


def test_gstreamer():
    """Check GStreamer support and test a simple pipeline."""
    print("\n----- GStreamer Test -----")
    build_info = cv2.getBuildInformation()
    if "GStreamer" in build_info:
        print(f"{Colors.GREEN}✓ GStreamer support in OpenCV{Colors.RESET}")
        pipeline = "videotestsrc pattern=smpte ! videoconvert ! appsink"
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                print(f"  Frame read successfully: {w}x{h}")
            else:
                print(f"{Colors.RED}✗ Failed to read frame{Colors.RESET}")
            cap.release()
        except Exception as e:
            print(f"{Colors.RED}✗ Pipeline error: {e}{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ No GStreamer support in OpenCV{Colors.RESET}")


def test_camera(index=0, backend=None, pipeline=None):
    """Open and test a camera, return True if successful."""
    backend_name = next(
        (name for name, b in BACKENDS.items() if b == backend), "default"
    )
    print(f"\nTesting camera {index} | Backend: {backend_name}")

    if pipeline:
        if not hasattr(cv2, "CAP_GSTREAMER"):
            print(f"{Colors.RED}✗ GStreamer not available{Colors.RESET}")
            return False
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    elif backend:
        cap = cv2.VideoCapture(index, backend)
    else:
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"{Colors.RED}✗ Could not open camera{Colors.RESET}")
        return False

    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"  Resolution: {w}x{h} | FPS: {fps:.2f}")

    ret, _ = cap.read()
    cap.release()
    if not ret:
        print(f"{Colors.RED}✗ Failed to read frame{Colors.RESET}")
        return False

    print(f"{Colors.GREEN}✓ Camera opened successfully{Colors.RESET}")
    return True


def main():
    print_info()
    available_backends = check_backends()
    test_gstreamer()
    return available_backends


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test camera with OpenCV")
    parser.add_argument(
        "--backend",
        type=str,
        choices=[b.lower() for b in BACKENDS],
        help="Camera backend to use",
    )
    parser.add_argument("--index", type=int, default=0, help="Camera index")
    parser.add_argument("--pipeline", type=str, help="GStreamer pipeline string")
    args = parser.parse_args()

    available_backends = main()

    selected_backend = BACKENDS.get(args.backend.upper()) if args.backend else None
    success = test_camera(
        index=args.index, backend=selected_backend, pipeline=args.pipeline
    )
    sys.exit(0 if success else 1)
