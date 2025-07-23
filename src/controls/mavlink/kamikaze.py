import time

from pymavlink import mavutil


class KamikazeDrone:
    def __init__(self, connection_string="udp:127.0.0.1:14550", logging=None):
        self.master = mavutil.mavlink_connection(connection_string)
        self.log = lambda _: None if logging is None else logging

        self.log("Connecting to kamikaze vehicle...")
        self.master.wait_heartbeat()
        self.log(
            f"Heartbeat received from system {self.master.target_system} component {self.master.target_component}"
        )

    def _arm_vehicle(self):
        self.log("Arming vehicle...")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        time.sleep(2)

    def set_mode_auto(self):
        self.log("Setting mode to AUTO...")
        self.master.set_mode_auto()
        time.sleep(1)

    def _clear_mission(self):
        self.log("Clearing existing mission...")
        self.master.waypoint_clear_all_send()
        time.sleep(1)

    def launch_kamikaze(self, target_lat, target_lon, target_alt=0):
        self._clear_mission()
        self._arm_vehicle()
        self.set_mode_auto()

        self.log("Uploading kamikaze mission...")

        # Define waypoints
        mission_items = [
            # Takeoff point
            self.master.mav.mission_item_encode(
                self.master.target_system,
                self.master.target_component,
                0,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0,
                0,
                0,
                0,
                0,
                target_lat,
                target_lon,
                20,  # Takeoff from near the crash point
            ),
            # Crash target
            self.master.mav.mission_item_encode(
                self.master.target_system,
                self.master.target_component,
                1,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                0,
                0,
                0,
                0,
                0,
                target_lat,
                target_lon,
                target_alt,  # Final waypoint (crash site)
            ),
        ]

        # Send mission count
        self.master.mav.mission_count_send(
            self.master.target_system, self.master.target_component, len(mission_items)
        )

        # Send each mission item
        for i, item in enumerate(mission_items):
            while True:
                msg = self.master.recv_match(type="MISSION_REQUEST", blocking=True)
                if msg.seq == i:
                    self.master.mav.send(item)
                    self.log(f"Sent mission item {i}")
                    break

        # Wait for MISSION_ACK
        self.master.recv_match(type="MISSION_ACK", blocking=True)
        self.log("Mission upload complete.")

        # Start mission
        self.log("Starting mission...")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_MISSION_START,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )

        # Monitor progress
        while True:
            msg = self.master.recv_match(blocking=True)
            if msg.get_type() == "MISSION_ITEM_REACHED":
                self.log(f"Reached waypoint: {msg.seq}")
            elif msg.get_type() == "HEARTBEAT":
                if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED == 0:
                    self.log("Drone disarmed. Mission likely complete.")
                    break

    def launch_kamikaze_complex(self, target_lat, target_lon, target_alt=0):
        """
        This is may be inaccurate need to verify. Written by chatGPT.
        A complex dramatic maneuver.
        """
        self._clear_mission()
        self._arm_vehicle()
        self.set_mode_auto()

        self.log("Uploading kamikaze mission...")

        # Define the approach point: a little higher than the crash point
        approach_lat = target_lat - 0.0001  # some offset for approach (50m)
        approach_lon = target_lon
        approach_alt = 30  # high enough for a dramatic descent

        # Define the steep descent path with intermediate points
        mission_items = [
            # Approach point
            self.master.mav.mission_item_encode(
                self.master.target_system,
                self.master.target_component,
                0,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                0,
                0,
                0,
                0,
                0,
                approach_lat,
                approach_lon,
                approach_alt,  # Higher point to approach from
            ),
            # Intermediate steep descent waypoint
            self.master.mav.mission_item_encode(
                self.master.target_system,
                self.master.target_component,
                1,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                0,
                0,
                0,
                0,
                0,
                target_lat,
                target_lon,
                10,  # Start the descent
            ),
            # Final crash waypoint
            self.master.mav.mission_item_encode(
                self.master.target_system,
                self.master.target_component,
                2,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                0,
                0,
                0,
                0,
                0,
                target_lat,
                target_lon,
                target_alt,  # Crash at target (altitude 0)
            ),
        ]

        # Send mission count
        self.master.mav.mission_count_send(
            self.master.target_system, self.master.target_component, len(mission_items)
        )

        # Send each mission item
        for i, item in enumerate(mission_items):
            while True:
                msg = self.master.recv_match(type="MISSION_REQUEST", blocking=True)
                if msg.seq == i:
                    self.master.mav.send(item)
                    self.log(f"Sent mission item {i}")
                    break

        # Wait for MISSION_ACK
        self.master.recv_match(type="MISSION_ACK", blocking=True)
        self.log("Mission upload complete.")

        # Start mission
        self.log("Starting mission...")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_MISSION_START,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )

        # Monitor progress
        while True:
            msg = self.master.recv_match(blocking=True)
            if msg.get_type() == "MISSION_ITEM_REACHED":
                self.log(f"Reached waypoint: {msg.seq}")
            elif msg.get_type() == "HEARTBEAT":
                if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED == 0:
                    self.log("Drone disarmed. Mission likely complete.")
                    break
