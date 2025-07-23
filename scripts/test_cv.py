#!/bin/python3
import argparse
import platform
import sys
import time

import cv2
import numpy as np


def main():
    print("\n===== OpenCV Test Results =====")
    # Basic OpenCV information
    print(f"OpenCV version: {cv2.__version__}")
    print(f"Python version: {platform.python_version()}")
    print(f"NumPy version: {np.__version__}")

    # Check available backends
    print("\n----- Available Backends -----")
    backends = [
        cv2.CAP_ANY,  # Auto detect
        cv2.CAP_V4L,  # V4L/V4L2
        cv2.CAP_V4L2,  # V4L2
        cv2.CAP_GSTREAMER,  # GStreamer
        cv2.CAP_FFMPEG,  # FFMPEG
    ]

    backend_names = [
        "AUTO",
        "V4L",
        "V4L2",
        "GSTREAMER",
        "FFMPEG",
    ]

    for idx, backend in enumerate(backends):
        try:
            # Just testing if we can create a VideoCapture object with this backend
            temp_cap = cv2.VideoCapture(0, backend)
            is_available = temp_cap.isOpened()
            temp_cap.release()
        except Exception as e:
            is_available = False
            error = str(e)

        status = "✅ Available" if is_available else "❌ Not available"
        print(f"{backend_names[idx]}: {status}")

    # Check if GStreamer is available specifically
    print("\n----- GStreamer Support -----")
    try:
        # Check if GStreamer support is built in
        if cv2.getBuildInformation().find("GStreamer") != -1:
            gstreamer_status = "✅ GStreamer support built into OpenCV"

            # Try a simple GStreamer pipeline
            try:
                pipeline = "videotestsrc pattern=smpte ! videoconvert ! appsink"
                cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                ret, frame = cap.read()
                if ret:
                    print("✅ Successfully read a frame from GStreamer test pipeline")
                    h, w = frame.shape[:2]
                    print(f"   Frame dimensions: {w}x{h}")
                else:
                    print("❌ Failed to read frame from GStreamer test pipeline")
                cap.release()
            except Exception as e:
                print(f"❌ Error testing GStreamer pipeline: {str(e)}")
        else:
            gstreamer_status = "❌ No GStreamer support in OpenCV build"
    except Exception as e:
        gstreamer_status = f"❌ Error checking GStreamer support: {str(e)}"

    print(gstreamer_status)

    # Print build information
    # print("\n----- OpenCV Build Information -----")
    # print(cv2.getBuildInformation())


def test_camera(backend=None, index=0, pipeline=None):
    print(
        f"Testing camera index {index} with backend: {backend if backend else 'default'}"
    )

    if pipeline:
        if not hasattr(cv2, "CAP_GSTREAMER"):
            print("ERROR: GStreamer support not available in OpenCV")
            return False
        print(f"Using GStreamer pipeline: {pipeline}")
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    elif backend:
        cap = cv2.VideoCapture(index, backend)
    else:
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print("ERROR: Could not open camera")
        return False

    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"\nResolution: {width}x{height}")
    print(f"FPS: {fps}")

    ret, _ = cap.read()
    if not ret:
        print("ERROR: Failed to read frame")
        return
    cap.release()

    print("Camera opened successfully")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test camera with OpenCV")
    parser.add_argument(
        "--backend",
        type=str,
        choices=["any", "v4l", "v4l2", "gstreamer", "ffmpeg"],
        help="Camera backend to use",
    )

    parser.add_argument("--index", type=int, default=0, help="Camera index")
    parser.add_argument("--pipeline", type=str, help="GStreamer pipeline string")
    args = parser.parse_args()

    main()
    backend_map = {
        "any": cv2.CAP_ANY,
        "v4l": cv2.CAP_V4L,
        "v4l2": cv2.CAP_V4L2,
        "gstreamer": cv2.CAP_GSTREAMER,
        "ffmpeg": cv2.CAP_FFMPEG,
    }

    backend = backend_map.get(args.backend) if args.backend else None

    success = test_camera(backend, args.index, args.pipeline)
    sys.exit(0 if success else 1)
