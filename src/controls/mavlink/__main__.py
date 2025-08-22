import time

import cv2

from src.controls.mavlink.ardupilot import ArdupilotConnection, Waypoint
from src.controls.mavlink.gz import (
    GazeboVideoCapture,
    enable_streaming,
    point_gimbal_downward,
)

## THIS FILE IS MAINLY FOR TESTING PURPOSES
connection = ArdupilotConnection("udp:127.0.0.1:14550")


connection.set_mode("AUTO")
connection.arm()
enable_streaming()
point_gimbal_downward()

camera = GazeboVideoCapture()
cap = camera.get_capture()

connection.takeoff(10)

location = connection.get_relative_gps_location()
if not location:
    exit(1)
lat, lon, alt = location
mission = [
    [lat + 0.00001, lon + 0.00001, 3],
    [lat - 0.00002, lon - 0.00002, 3],
    [lat + 0.00002, lon + 0.00002, 3],
    [lat - 0.00001, lon + 0.00001, 3],
    [lat + 0.00002, lon + 0.00001, 3],
    [lat + 0.00002, lon - 0.00002, 3],
    [lat, lon, alt + 3],  # Return to home
]


def _imshow(guided_mode=False):
    ret, frame = camera.read()
    if not ret:
        connection.log("Failed to capture frame.")
        return True
    # write text guided mode
    if guided_mode:
        cv2.putText(
            frame,
            "Repositioning in progress...",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
    cv2.imshow("Gazebo Video Stream", frame)

    key = cv2.waitKey(30) & 0xFF
    # if key == ord("q"):
    # 	connection.log("User exited video stream.")
    # 	return True


# THIS IS WRITTEN TO PROVE THAT
# SANDWICHED BETWEEN MISSION WAYPOINTS,
# THE DRONE CAN BE REPOSITIONED
prev_seq = 1


def _update_status_hook(seq, completed):
    # after waypoint is reached, set to GUIDED mode, move to base, and then set back to AUTO
    global prev_seq
    if not completed:
        connection.log(f"Current waypoint: {seq} {prev_seq}")
        if seq == prev_seq + 1:
            connection.log(f"Reached waypoint {seq}, setting to GUIDED mode.")
            connection.set_mode("GUIDED")
            connection.goto_waypointv2(lat, lon, 10)
            while not connection.check_reposition_reached(lat, lon, 10):
                _imshow(True)
                time.sleep(0.1)
            connection.log(f"Waypoint {seq} reached, setting to AUTO mode.")
            connection.set_mode("AUTO")
            prev_seq = seq


try:
    connection.upload_mission(
        [Waypoint(lat, lon, alt, hold=0) for lat, lon, alt in mission]
    )

    connection.start_mission()
    while not connection.monitor_mission_progress(callback=_update_status_hook):
        _imshow()
        time.sleep(0.1)
except Exception as e:
    connection.log(f"❌ Error during mission upload: {e}")
finally:
    connection.clear_mission()
    connection.return_to_launch()
    connection.close()
    connection.log("Connection closed.")
    connection.log("Ardupilot connection example completed.")
