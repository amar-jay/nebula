import time

import pygame

from src.controls.mavlink import ardupilot

CONNECTION_STR = "udp:127.0.0.1:14550"
SAVE_DIR = "captures"  # directory to save images
PER_CAPTURE = 1  # time in seconds to wait between captures

master = ardupilot.ArdupilotConnection(CONNECTION_STR)
print(
    f"[MAVLink] Heartbeat from system {master.target_system}, component {master.target_component}"
)


# gz.arm_and_takeoff(master, target_altitude=10.0)

# done = gz.point_gimbal_downward()
# if not done:
#    print("❌ Failed to point gimbal downward.")
#    exit(1)

# done = gz.enable_streaming(
#    world="delivery_runway",
#    model_name="iris_with_gimbal",
#    camera_name="camera")
# if not done:
#    print("❌ Failed to enable streaming.")
#    exit(1)


location = master.get_relative_gps_location()
if location is None:
    print("❌ Failed to get current GPS location.")
    exit(1)

lat, lon, alt = location
print(f"📍 Current location → lat: {lat}, lon: {lon}, alt: {alt}")


def send_manual_control(x, y, z, r, buttons=0):
    master.master.mav.manual_control_send(
        master.target_system,
        x,  # pitch
        y,  # roll
        z,  # throttle
        r,  # yaw
        buttons,
    )


pygame.init()
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)
joystick.init()

while True:
    pygame.event.pump()
    print(
        joystick.get_axis(0),
        joystick.get_axis(1),
        joystick.get_axis(2),
        joystick.get_axis(3),
    )

    x = int(joystick.get_axis(0) * 1000)  # Roll
    y = int(joystick.get_axis(1) * 1000)  # Pitch
    r = int(joystick.get_axis(2) * 1000)  # Yaw
    z = int(
        ((-joystick.get_axis(3) + 1) / 2) * 1000
    )  # Throttle (convert -1..1 to 0..1000)

    send_manual_control(x, y, z, r)
    time.sleep(0.05)
