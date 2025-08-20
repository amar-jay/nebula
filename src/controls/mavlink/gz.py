import math
import re
import subprocess
import time

import cv2
import numpy as np
from pymavlink import mavutil

from src.controls.mavlink.ardupilot import ArdupilotConnection


class GazeboVideoCapture:
    def __init__(self, camera_port=5600, fps=30):
        """
        Open a video stream from the Gazebo simulation.
        """

        pipeline = (
            f"udpsrc port={camera_port} ! "
            "application/x-rtp, encoding-name=H264 ! "
            "rtph264depay ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "videorate ! "
            f"video/x-raw,framerate={fps}/1 ! "
            "appsink"
        )

        print(f"Using GStreamer pipeline: {pipeline}")
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"VideoCapture opened with pipeline: {pipeline}")

        if not self.cap.isOpened():
            raise RuntimeError(
                "Failed to open stream! Check sender or pipeline. pipeline=", pipeline
            )
        # move all methods of self.cap to self

    def __getattr__(self, name):
        """
                Forward any undefined attribute access to self.cap
        This will automatically delegate any method calls not defined in this class
        to the underlying cv2.VideoCapture object.
        """
        return getattr(self.cap, name)

    def get_capture(self):
        return self.cap

    def get_frame_size(self):
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # fps = self.cap.get(cv2.CAP_PROP_FPS)
        return width, height, None

    def close(self):
        """
        Close the video capture stream.
        """
        if self.cap.isOpened():
            self.cap.release()
            cv2.destroyAllWindows()
            print("Video capture stream closed.")
        else:
            print("Video capture stream was not opened.")


class GazeboConnection(ArdupilotConnection):
    def __init__(
        self,
        connection_string,
        camera_port=5600,
        logger=None,
    ):
        super().__init__(
            connection_string,
            logger=lambda *args: (
                logger(*args) if logger else print("[GazeboConnection]", *args)
            ),
        )
        self.camera_port = camera_port
        self.cap = GazeboVideoCapture(camera_port=camera_port)


def enable_streaming(
    model_name="iris_with_stationary_gimbal",
    camera_link="tilt_link",
    world="delivery_runway",
    log=print,
) -> bool:
    """
    Enable streaming for the camera in the Gazebo simulation.
    """
    command = [
        "gz",
        "topic",
        "-t",
        f"/world/{world}/model/{model_name}/model/gimbal/link/{camera_link}/sensor/camera/image/enable_streaming",
        # "/world/our_runway/model/iris_with_gimbal/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming",
        "-m",
        "gz.msgs.Boolean",
        "-p",
        "data: 1",
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.5)
        log("🦾 Gazebo gimbal streaming enabled...", result.stdout)
        print("running", " ".join(command))

        return True
    except subprocess.CalledProcessError as e:
        log("Error:", e.stderr)
        log("The current topic is", " ".join(command))
        return False
    except Exception as e:
        log("Error:", e)


def point_gimbal_downward(topic="/gimbal/cmd_tilt", angle=0) -> bool:
    """
    Uses gz command line to point gimbal downward.
    """
    command = [
        "gz",
        "topic",
        "-t",
        f"{topic}",
        "-m",
        "gz.msgs.Double",
        "-p",
        f"data: {angle}",
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("[CAMERA] Gimbal pointed to angle:", angle, "degrees. On topic:", topic)
        return True
    except subprocess.CalledProcessError as e:
        print("Error:", e.stderr)
        return False


def get_camera_params(
    model_name="iris_with_stationary_gimbal",
    camera_link="tilt_link",
    world="delivery_runway",
    timeout: float = 20.0,
):
    topic = f"/world/{world}/model/{model_name}/model/gimbal/link/{camera_link}/sensor/camera/camera_info"
    cmd = ["gz", "topic", "-e", "-t", topic]
    print("Running command:", " ".join(cmd))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    start_time = time.time()
    k_values = []
    d_values = []
    found_intrinsics = False
    found_distortion = False

    try:
        for line in process.stdout:
            if "intrinsics" in line:
                found_intrinsics = True
                found_distortion = False
                continue
            elif "distortion" in line:
                found_distortion = True
                found_intrinsics = False
                continue

            if found_intrinsics:
                match = re.search(r"k:\s*([0-9.eE+-]+)", line)
                if match:
                    k_values.append(float(match.group(1)))
                    if len(k_values) == 9:
                        found_intrinsics = False

            elif found_distortion:
                match = re.search(r"k:\s*([0-9.eE+-]+)", line)
                if match:
                    d_values.append(float(match.group(1)))
                    if len(d_values) == 5:
                        found_distortion = False

            if len(k_values) == 9 and len(d_values) == 5:
                break

            if time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for camera info.")

        process.terminate()
        process.wait(timeout=1)

        if len(k_values) != 9:
            raise ValueError("Failed to extract full K matrix")
        if len(d_values) != 5:
            raise ValueError("Failed to extract distortion coefficients")

        K = np.array(k_values).reshape(3, 3)
        D = np.array(d_values)
        return {"camera_intrinsics": K, "distortion": D}

    except Exception as e:
        process.kill()
        print("Error:", e)
        return None


def goto_waypoint_basic(master, lat: float, lon: float, alt: float):
    """Send MAV_CMD_NAV_WAYPOINT to fly to (lat, lon, alt)."""
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0,  # confirmation
        0,
        0,
        0,
        0,  # params 1-4 unused
        lat,  # param 5: latitude
        lon,  # param 6: longitude
        alt,  # param 7: altitude (AMSL)
    )
    print(f"[MAVLink] Sent waypoint → lat: {lat}, lon: {lon}, alt: {alt}")


def goto_waypoint_sync(
    master, lat: float, lon: float, alt: float, radius_m=2.0, alt_thresh=1.0, timeout=20
):
    """
    Send drone to waypoint (lat, lon, alt) and wait until it's close enough.

    Args
        master: MAVLink Connection (pymavlink instance).
        lat, lon: Target latitude/longitude in degrees.
        alt: Target altitude in meters (AMSL).
        radius_m: Horizontal threshold in meters to consider "arrived".
        alt_thresh: Vertical (altitude) threshold in meters.
        timeout: Max seconds to wait for arrival.
    """
    # Send command
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0,
        0,
        0,
        0,
        0,
        lat,
        lon,
        alt,
    )
    print(f"[MAVLink] Sent waypoint → lat={lat}, lon={lon}, alt={alt}")

    # Convert lat/lon to scaled int32 used in GLOBAL_POSITION_INT
    target_lat = int(lat * 1e7)
    target_lon = int(lon * 1e7)
    target_alt = int(alt * 1000)  # in mm

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    start_time = time.time()
    while time.time() - start_time < timeout:
        msg = master.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=1)
        if msg:
            current_lat = msg.lat
            current_lon = msg.lon
            current_alt = msg.alt  # in mm

            # compute distance
            dist = haversine(
                current_lat / 1e7, current_lon / 1e7, target_lat, target_lon
            )
            alt_diff = abs(current_alt - target_alt) / 1000.0

            print(f"Distance: {dist:.1f} m, Alt diff: {alt_diff:.2f} m")

            if dist <= radius_m and alt_diff <= alt_thresh:
                print("✅ Reached waypoint.")
                return True
        else:
            print("⚠️ No GLOBAL_POSITION_INT received.")

    print("❌ Timeout: did not reach waypoint in time.")
    return False


if __name__ == "__main__":
    print(
        get_camera_params(
            model_name="iris_with_stationary_gimbal",
            camera_link="tilt_link",
            world="delivery_runway",
        )
    )
    # enable_streaming()
    # connection = ArdupilotConnection(
    #     connection_string="udp:127.0.0.1:14550",
    #     logger=lambda *args: print("[GazeboConnection]", *args),
    # )

    # connection.arm()
    # # point_gimbal_downward()

    # connection.takeoff(10)

    # cap = GazeboVideoCapture()
    # connection.set_mode("AUTO")

    # _lat, _lon, _ = connection.get_relative_gps_location()

    # connection.goto_waypoint(_lat + 0.00001, _lon + 0.00001, 3)

    # camera = cap.get_capture()

    # while True:
    #     if connection.check_reposition_reached(_lat + 0.00001, _lon + 0.00001, 3):
    #         connection.log("Waypoint reached!")
    #         break
    #     ret, frame = camera.read()
    #     if not ret:
    #         connection.log("Failed to capture frame.")
    #         break
    #     cv2.imshow("Gazebo Video Stream", frame)
    #     key = cv2.waitKey(30) & 0xFF
    #     if key == ord("q"):
    #         connection.log("User exited video stream.")
    #         break
    # connection.return_to_launch()
    # connection.clear_mission()
    # connection.close()
    # connection.log("Connection closed.")
    # connection.log("Ardupilot connection example completed.")
