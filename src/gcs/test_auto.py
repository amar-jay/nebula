import time

from src.controls.mavlink import ardupilot
from src.controls.mavlink.mission_types import Waypoint

drone = ardupilot.ArdupilotConnection(connection_string="udp:127.0.0.1:14550")
drone.set_mode("GUIDED")
home_position = drone.get_relative_gps_location()
drone.arm()
drone.takeoff(target_altitude=10)

mission_waypoints = [
    Waypoint(*home_position),
    Waypoint(40.95896591, 29.13568128, 5, 3),
    Waypoint(40.95897731, 29.13589263, 5, 3),
    Waypoint(40.95876277, 29.13590910, 5, 3),
    Waypoint(40.95880616, 29.13567155, 5, 3),
]

drone.clear_mission()
drone.upload_mission(mission_waypoints)
drone.start_mission()


# Simple states
class WaypointState:
    FLYING_AUTO = "flying_auto"
    POSITIONING = "positioning"
    WAITING_DROP = "waiting_drop"
    WAITING_RAISE = "waiting_raise"


# State variables
current_state = WaypointState.FLYING_AUTO
current_waypoint = 0
target_lat = 0
target_lon = 0
target_alt = 0


def drop_hook():
    drop_hook_confirm = input("Drop hook? (y/n): ")
    if drop_hook_confirm.lower() == "y":
        print("Dropping hook...")
        return True
    return False


def raise_hook():
    raise_hook_confirm = input("Raise hook? (y/n): ")
    if raise_hook_confirm.lower() == "y":
        print("Raising hook...")
        return True
    return False


def get_helipad_gps(i: int):
    w = mission_waypoints[i]
    return w.lat, w.lon, 15


try:
    while True:
        if current_state == WaypointState.FLYING_AUTO:
            msg = drone.master.recv_match(type=["MISSION_ITEM_REACHED"], blocking=False)

            if msg and msg.seq > 0:
                print(f"Reached waypoint {msg.seq}")
                current_waypoint = msg.seq

                if msg.seq >= len(mission_waypoints) - 1:
                    print("Mission completed")
                    break

                # Switch to guided mode and start positioning
                drone.set_mode("GUIDED")
                target_lat, target_lon, target_alt = get_helipad_gps(msg.seq)
                drone.goto_waypointv2(
                    alt=target_alt, lat=target_lat, lon=target_lon, timeout=100, speed=1
                )
                current_state = WaypointState.POSITIONING

        elif current_state == WaypointState.POSITIONING:
            if drone.check_reposition_reached(
                _alt=target_alt, _lat=target_lat, _lon=target_lon
            ):
                current_state = WaypointState.WAITING_DROP

        elif current_state == WaypointState.WAITING_DROP:
            if drop_hook():
                current_state = WaypointState.WAITING_RAISE
            else:
                # Skip hook operations, go back to auto
                drone.set_mode("AUTO")
                current_state = WaypointState.FLYING_AUTO

        elif current_state == WaypointState.WAITING_RAISE:
            if raise_hook():
                print("Hook operations completed")
            else:
                print("Hook raise cancelled")

            # Resume auto flight
            drone.set_mode("AUTO")
            current_state = WaypointState.FLYING_AUTO

except KeyboardInterrupt:
    print("Mission interrupted by user.")
    drone.clear_mission()
except Exception as e:
    print(f"Error occurred: {e}")
