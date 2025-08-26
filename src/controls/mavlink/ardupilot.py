import logging
import math
import time
from dataclasses import dataclass

import pymavlink.dialects.v20.all as dialect
from pymavlink import mavutil

from src.controls.mavlink.mission_types import Waypoint


@dataclass
class WaypointState:
    FLYING_AUTO = "flying_auto"
    POSITIONING = "positioning"
    WAITING_DROP = "waiting_drop"
    WAITING_RAISE = "waiting_raise"


class ArdupilotConnection:
    def __init__(self, connection_string, wait_heartbeat=10, logger=None):
        self.connection_string = connection_string
        self.target_system = 1
        self.target_component = 1
        self.master = mavutil.mavlink_connection(connection_string, baudrate=57600)
        self.master.wait_heartbeat(timeout=wait_heartbeat)
        # timeout for heartbeat
        if not self.master:
            raise ConnectionError(
                f"Failed to connect to {connection_string} within {wait_heartbeat} seconds"
            )
        self.log = self._set_logger(logger)
        self.log(
            f"Connected to {self.connection_string} with system ID {self.master.target_system}",
            "info",
        )
        self.current_state = WaypointState.FLYING_AUTO

        self.status = {
            "home": None,
            "mode": self.master.flightmode,
            "connected": False,
            "armed": False,
            "flying": False,
            "position": None,
            "orientation": None,
            "mission_active": False,
            "current_waypoint": -1,
            "total_waypoints": 0,
            "battery": 100,
        }

    def fetch_home(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_GET_HOME_POSITION,
            0,  # confirmation
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # unused parameters
        )

    def _set_logger(self, logger):
        # if logger is an instance of logging.Logger, set it
        # else if logger is a callable, use it as a function
        # else use print prepended with [MAVLink]
        if isinstance(logger, logging.Logger):

            def _logger(arg, _type):
                if _type == "info":
                    logger.info(arg)
                elif _type == "success":
                    logger.success(arg)
                elif _type == "warning":
                    logger.warning(arg)
                elif _type == "error":
                    logger.error(arg)
                else:
                    logger.debug(arg)

            return _logger
        elif callable(logger):
            return logger
        else:

            def _logger(arg, _type):
                if _type == "info":
                    print("[MAVLink] ", arg)
                elif _type == "success":
                    print("[MAVLink] ✅ ", arg)
                elif _type == "warning":
                    print("[MAVLink] ⚠️ ", arg)
                elif _type == "error":
                    print("[MAVLink] ❌ ", arg)
                else:
                    print("[MAVLink] ", arg)

            return _logger

    def set_mode(self, mode):
        mode_id = self.master.mode_mapping()[mode]
        self.master.set_mode(mode_id)

    def get_mode(self):
        return self.master.flightmode

    def ack_sync(self, msg, timeout=10):
        now = time.time()
        while True:
            if time.time() - now > timeout:
                return
            m = self.master.recv_match(type=msg, blocking=True)
            if m is not None:
                if m.get_type() == msg:
                    return m
                self.log(f"Received {m.get_type()} instead of {msg}", "warning")
            else:
                continue

    def repeat_relay(self, delay=10):
        """
        DO REPEAT RELAY: NOTE: unstable, unknown,
        """
        # Wait for a heartbeat from the vehicle
        self.log("Repeating relay...", "info")

        # Arm the vehicle
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_REPEAT_RELAY,
            1,  # relay instance number
            1,  # param2: cycle count
            delay,  # param3: delay in seconds
            0,
            0,
            0,
            0,
            0,  # Arm (1 to arm, 0 to disarm)
        )

    def arm(self):
        """
        Arms the vehicle and sets it to GUIDED mode.
        """
        print("Arming the vehicle...")
        # Wait for a heartbeat from the vehicle
        self.log("Waiting for heartbeat...", "info")
        self.master.wait_heartbeat()
        self.log(f"Heartbeat received from system {self.master.target_system}", "info")

        # Set mode to GUIDED (or equivalent)
        # self.set_mode("GUIDED")

        # Arm the vehicle
        self.log("Arming motors...", "info")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # Confirmation
            1,
            0,
            0,
            0,
            0,
            0,
            0,  # Arm (1 to arm, 0 to disarm)
        )

    def safety_switch(self, state):
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_DECODE_POSITION_SAFETY,
            1 if state else 0,
        )
        # self.ack_sync("COMMAND_ACK")

    def disarm(self):
        """
        Disarms the vehicle.
        """
        self.log("Disarming motors...", "info")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # Confirmation
            0,  # Disarm (1 to arm, 0 to disarm)
            0,  # param2 (force, can be set to 21196 to force disarming)
            0,  # param3 (unused)
            0,  # param4 (unused)
            0,  # param5 (unused)
            0,  # param6 (unused)
            0,  # param7 (unused)
        )

        self.master.motors_disarmed_wait()
        self.log("Vehicle disarmed!", "info")

    def takeoff(self, target_altitude=5.0, wait_time=10):
        """
        Initiates takeoff to target altitude in meters.
        """

        # Send takeoff command
        self.log(f"Taking off to {target_altitude} meters...", "info")
        self.set_mode("GUIDED")  # Ensure we're in GUIDED mode
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,  # Confirmation
            0,
            0,
            0,
            0,
            0,
            0,
            target_altitude,  # Altitude
        )

        # Optional: wait for some time or monitor altitude via message stream
        time.sleep(wait_time)  # crude wait; replace with altitude monitor if needed

        self.log("Takeoff command sent.", "info")

    def return_to_launch(self):
        self.set_mode("GUIDED")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0,  # Confirmation
            0,  # Param1: unused
            0,  # Param2: unused
            0,  # Param3: unused
            0,  # Param4: unused
            0,  # Param5: unused
            0,  # Param6: unused
            0,  # Param7: unused
        )
        self.ack_sync("COMMAND_ACK")

    def land(self):
        self.log("Landing...", "info")
        self.set_mode("GUIDED")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,  # Confirmation
            0,  # Param1: unused
            0,  # Param2: unused
            0,  # Param3: unused
            0,  # Param4: unused
            0,  # Param5: unused
            0,  # Param6: unused
            0,  # Param7: unused
        )
        self.ack_sync("COMMAND_ACK")

    def upload_mission(self, waypoints: list[Waypoint]):
        num_wp = len(waypoints)
        self.num_wp = num_wp
        self.log(f"Uploading {num_wp} waypoints...", "info")

        # send mission count
        self.master.mav.mission_count_send(
            self.master.target_system, self.master.target_component, num_wp
        )
        self.ack_sync("MISSION_REQUEST")
        for i, waypoint in enumerate(waypoints):
            # send mission item
            self.master.mav.mission_item_send(
                target_system=self.master.target_system,  # System ID
                target_component=self.master.target_component,  # Component ID
                seq=i,  # Sequence number for item within mission (indexed from 0).
                frame=dialect.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # The coordinate system of the waypoint.
                command=dialect.MAV_CMD_NAV_WAYPOINT,
                current=(1 if i == 0 else 0),
                autocontinue=0,
                param1=waypoint.hold,  # 	Hold time. (ignored by fixed wing, time to stay at waypoint for rotary wing)
                param2=0,  # Acceptance radius (if the sphere with this radius is hit, the waypoint counts as reached)
                param3=0,  # 	Pass the waypoint to the next waypoint (0 = no, 1 = yes)
                param4=0,  # Desired yaw angle at waypoint (rotary wing). NaN to use the current system yaw heading mode (e.g. yaw towards next waypoint, yaw to home, etc.).
                x=waypoint.lat,  # Latitude in degrees * 1E7
                y=waypoint.lon,  # Longitude in degrees * 1E7
                z=waypoint.alt,  # Altitude in meters (AMSL) DOESN'T TAKE alt/1000 nor compensated altitude
            )
            if i != num_wp - 1:
                self.ack_sync("MISSION_REQUEST")
                self.log(f"Waypoint {i} uploaded", "info")

        self.ack_sync("MISSION_ACK")
        self.log("Mission upload complete.", "info")

    def clear_mission(self):
        # Clear mission
        self.log("Clearing all missions. Hack...", "info")
        # Set to GUIDED mode explicitly (you can also use MAV_MODE_AUTO if that suits your logic)
        # self.master.set_mode("GUIDED")  # Or use command_long if you don't have helper
        self.master.mav.mission_clear_all_send(
            self.master.target_system, self.master.target_component
        )
        ack = self.master.recv_match(type='MISSION_ACK', blocking=True, timeout=3)
        self.num_wp = 0
        return ack


    def start_mission(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_MISSION_START,
            0,  # Confirmation
            0,  # Param1: unused
            0,  # Param2: unused
            0,  # Param3: unused
            0,  # Param4: unused
            0,  # Param5: unused
            0,  # Param6: unused
            0,  # Param7: unused
        )
        self.ack_sync("COMMAND_ACK")

    def get_relative_gps_location(self, blocking=True, timeout=1.0):
        """
        Get the current GPS location of the drone.
        Args:
                relative (bool): If True, returns relative altitude; otherwise, returns (relative altitude, absolute altitude) as altitude.
                timeout (float): Timeout for receiving GPS data.
        """
        msg = self.master.recv_match(
            type="GLOBAL_POSITION_INT", blocking=blocking, timeout=timeout
        )
        if not msg:
            if blocking:
                self.log("Timeout: Failed to receive GPS data.", "error")
            return None

        _lat = msg.lat / 1e7  # Convert from 1e7-scaled degrees to float degrees
        _lon = msg.lon / 1e7
        _ralt = (
            msg.relative_alt / 1000.0
        )  # Convert mm to meters (altitude above ground)
        # Select altitude based on `relative` flag
        return _lat, _lon, _ralt

    def get_amsl_gps_location(self, blocking=True, timeout=1.0):
        """
        Get the current GPS location of the drone.
        Args:
                relative (bool): If True, returns relative altitude; otherwise, returns (relative altitude, absolute altitude) as altitude.
                timeout (float): Timeout for receiving GPS data.
        """
        msg = self.master.recv_match(
            type="GLOBAL_POSITION_INT", blocking=blocking, timeout=timeout
        )
        if not msg:
            if blocking:
                self.log("Timeout: Failed to receive GPS data.", "error")
            return None

        _lat = msg.lat / 1e7  # Convert from 1e7-scaled degrees to float degrees
        _lon = msg.lon / 1e7
        _ralt = (
            msg.relative_alt / 1000.0
        )  # Convert mm to meters (altitude above ground)

        _alt = msg.alt / 1000.0  # Convert mm to meters (altitude AMSL)
        return _lat, _lon, _ralt, _alt

    def get_current_attitude(self, blocking=True, timeout=1.0):
        """
        Get the current attitude (roll, pitch, yaw) of the drone in radians.

        Returns:
            tuple: (roll, pitch, yaw) in radians
            None: If attitude data is not available
        """
        try:
            # Request attitude data
            # self.master.mav.request_data_stream_send(
            # 	self.master.target_system,
            # 	self.master.target_component,
            # 	mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,  # Attitude data
            # 	10,  # 10 Hz rate
            # 	1,  # Start sending
            # )

            # Wait for the attitude message
            # now = time.time()
            msg = self.master.recv_match(
                type="ATTITUDE", blocking=blocking, timeout=timeout
            )

            if msg:
                roll = msg.roll  # Roll angle in radians
                pitch = msg.pitch  # Pitch angle in radians
                yaw = msg.yaw  # Yaw angle in radians

                # Normalize yaw to [0, 2π] range if needed
                if yaw < 0:
                    yaw += 2 * math.pi
                # print("Time to fetch gps", time.time() - now)
                return (roll, pitch, yaw)
            else:
                if blocking:
                    self.log("Failed to get attitude data", "error")
                return None

        except Exception:
            self.log("MAVLink Error getting attitude", "error")
            return None

    def get_status(self):
        # Try receiving a few messages quickly
        for _ in range(20):
            msg = self.master.recv_match(
                type=[
                    "HEARTBEAT",
                    "HOME_POSITION",
                    "GLOBAL_POSITION_INT",
                    "ATTITUDE",
                    "MISSION_CURRENT",
                    "BATTERY_STATUS",
                    "VFR_HUD",
                ],
                blocking=False,
            )

            if not msg:
                continue
            if msg.get_type() == "HOME_POSITION":
                print("home position")
                self.status["home"] = {
                    "lat": msg.latitude / 1e7,
                    "lon": msg.longitude / 1e7,
                    "alt": msg.altitude / 1e3,
                }

            if msg.get_type() == "HEARTBEAT":
                self.status["connected"] = True
                self.status["armed"] = bool(self.master.motors_armed())
                self.status["flying"] = (
                    msg.system_status == mavutil.mavlink.MAV_STATE_ACTIVE
                )

            elif msg.get_type() == "GLOBAL_POSITION_INT":
                self.status["position"] = {
                    "lat": msg.lat / 1e7,
                    "lon": msg.lon / 1e7,
                    "alt": msg.relative_alt / 1e3,
                }
            elif msg.get_type() == "ATTITUDE":
                self.status["orientation"] = {
                    "roll": math.degrees(msg.roll),
                    "pitch": math.degrees(msg.pitch),
                    "yaw": math.degrees(msg.yaw),
                }

            elif msg.get_type() == "VFR_HUD":
                self.status["speed"] = msg.groundspeed  # In m/s

            elif msg.get_type() == "MISSION_CURRENT":
                if hasattr(msg, "seq"):
                    self.status["current_waypoint"] = msg.seq
                    self.status["mission_active"] = msg.seq > 0  # or some other logic
                if hasattr(msg, "total"):
                    self.status["total_waypoints"] = msg.total

            elif msg.get_type() == "BATTERY_STATUS":
                self.status["battery"] = msg.battery_remaining
            self.status["mode"] = self.master.flightmode

        return self.status

    def close(self):
        self.master.close()
        delattr(self, "master")
        self.log("Mavlink Connection closed.", "info")

    def goto_waypoint(
        self,
        lat: float,
        lon: float,
        alt: float,
    ):
        """
        Send command to move to the specified latitude, longitude, and altitude using MAV_CMD_NAV_WAYPOINT.
        Initiate waypoint navigation. This does not block.
        """
        self.log(f"Waypoint Set: lat={lat}, lon={lon}, alt={alt}", "info")
        self.master.mav.command_int_send(
            self.master.target_system,
            self.master.target_component,
            dialect.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            dialect.MAV_CMD_NAV_WAYPOINT,
            0,  # Current
            0,  # Autocontinue
            0,  # hold time
            0,  # acceptance radius
            0,  # pass radius
            float("nan"),  # yaw nan by default
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
        )
        self.log(f"Waypoint Sent: lat={lat}, lon={lon}, alt={alt}", "info")
        return

    def goto_waypointv2(
        self,
        lat: float,
        lon: float,
        alt: float,
        timeout=20,
        speed=-1,  # speed in m/s, default is 1 m/s
    ):
        """
        Send command to move to the specified latitude, longitude, and current altitude
        Initiate waypoint navigation. This does not block.
        """
        self.log(
            f"Waypoint Set: lat={lat}, lon={lon}, alt={alt}, timeout={timeout}", "info"
        )
        self.master.mav.command_int_send(
            self.master.target_system,
            self.master.target_component,
            dialect.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            # “frame” = 0 or 3 for alt-above-sea-level, 6 for alt-above-home or 11 for alt-above-terrain
            dialect.MAV_CMD_DO_REPOSITION,
            0,  # Current
            0,  # Autocontinue
            0,  # Hold time at waypoint (param1)
            speed if speed > 0 else 1,  # Acceptance radius (param2)
            0,  # Pass through waypoint (param3)
            0,  # Desired yaw angle (param4)
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
        )
        self.log(f"Waypoint Sent: lat={lat}, lon={lon}, alt={alt}", "info")
        return

    def set_speed(self, speed):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            dialect.MAV_CMD_DO_CHANGE_SPEED,
            0,  # Confirmation
            1,  # Speed type: 1 = ground speed
            speed,  # Speed in m/s
            0,  # Throttle (no change)
            0,
            0,
            0,
            0,  # Unused
        )

    # Send kamikaze GPS coordinate
    def goto_kamikaze(self, lat, lon):
        self.set_mode("GUIDED")
        self.set_speed(15)
        self.takeoff(20)
        self.goto_waypointv2(lat, lon, 1)

    def check_reposition_reached(self, _lat, _lon, _alt):
        location = self.get_relative_gps_location()
        if location is None:
            self.log("failed to get gps location", "error")
            return False
        lat, lon, alt = location
        # print(f"difference: {abs(_lat-lat)} , {abs(_lon-lon)}, {_alt}/{alt}")
        if abs(_lat - lat) < 5e-6 and abs(_lon - lon) < 5e-6 and abs(_alt - alt) < 1e-2:
            self.log("Reposition reached!", "success")
            return True

        return False

    def waypoint_reached(self):
        """
        Returns (True, seq) exactly once when a new waypoint is reached.
        After reading True, it resets automatically so the next call
        won't return True until another waypoint is reached.
        """
        # Persistent storage for last waypoint handled
        if not hasattr(self, "_last_reached_seq"):
            self._last_reached_seq = 0

        # Refresh status to get latest MISSION_CURRENT
        # self.get_status()  # must update self.status["current_waypoint"]. Its autoupdated

        seq = int(self.status.get("current_waypoint", -1))
        if seq > self._last_reached_seq:
            self._last_reached_seq = seq
            return True, seq

        return False, self._last_reached_seq

    def monitor_mission_progress(self, callback=None, timeout=None):
        """
        `callback` is called when a waypoint is reached it takes
        the current waypoint index and a completion flag as arguments
        """

        def func():
            msg = self.master.recv_match(
                type=["MISSION_ITEM_REACHED", "MISSION_CURRENT", "MISSION_COUNT"],
                blocking=False,
            )
            if not msg:
                return False
            elif msg.get_type() == "MISSION_ITEM_REACHED":
                if callback:
                    callback(msg.seq, False)
                # Check if we've reached the final waypoint
                if msg.seq == self.num_wp - 1:
                    self.log("Mission completed!", "success")
                    if callback:
                        callback(msg.seq, True)
                    return True
            elif msg.get_type() == "MISSION_COUNT":
                print("mission count...")
            return False

        if timeout is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if func():
                    return True
        else:
            return func()
        self.log("Mission monitoring timed out", "error")
        return False
    def set_mission_waypoint(self, wp:int):
        return self.master.mav.mission_set_current_send(
            self.master.target_system,
            self.master.target_component,
            wp
        )

    def monitor_mission_progressv2(
        self,
        is_auto=None,
        status_callback=None,
        helipad_gps=None,
        drop_hook=None,
        raise_hook=None,
        timeout=None,
    ):
        """
        `callback` is called when a waypoint is reached it takes
        the current waypoint index and a completion flag as arguments
        """

        def func():
            if self.current_state == WaypointState.FLYING_AUTO:
                reached, idx = self.waypoint_reached()
                # THIS METHOD DOESNT WORK SINCE MISSION ITEM REACHED IS RETURNED ONCE
                # if reached:
                # msg = self.master.recv_match(type=["MISSION_ITEM_REACHED"], blocking=False)
                # print(f"{idx=}")
                # if status_callback:
                #     status_callback(current=idx, done=False, state="AUTO")

                # if msg:
                #   print("Checking for mission progress...")

                #TODO: set state for initial condition. for idx=0. drop and raise hook but no stabilization
                if reached and idx > 1: 
                    print(f"{reached=}   {idx=} {self.num_wp-1} {self._last_reached_seq}")
                    print(f"Reached waypoint {idx}")

                    if idx >= self.num_wp - 1:
                        if status_callback:
                            status_callback(current=idx, done=True, state="AUTO")
                        print("Mission completed")
                        if hasattr(self, "_target_lat"):
                          delattr(self, "_target_lat")
                        if hasattr(self, "_target_lon"):
                          delattr(self, "_target_lon")
                        self._last_reached_seq = 0

                        return True
                    if is_auto is not None and not is_auto(idx):
                        return False

                    # Switch to guided mode and start positioning
                    self.set_mode("GUIDED")
                    print("Switching to GUIDED mode")
                    if helipad_gps is None:
                        print("Helipad GPS coordinates not provided")
                        self.log("Helipad GPS coordinates not provided", "error")
                        self.current_state = WaypointState.FLYING_AUTO
                        self.set_mission_waypoint(self._last_reached_seq)
                        self.set_mode("AUTO")
                        return False
                    self._target_lat, self._target_lon = helipad_gps
                    if self._target_lat is not None and self._target_lon is not None:
                        self.goto_waypointv2(
                            alt=5,
                            lat=self._target_lat,
                            lon=self._target_lon,
                            timeout=100,
                            speed=1,
                        )
                        status_callback(current=idx, done=False, state="POSITIONING")
                        self.current_state = WaypointState.POSITIONING
                    else:
                        print("Invalid helipad GPS coordinates")
                        self.log("Invalid helipad GPS coordinates", "error")
                        self.current_state = WaypointState.FLYING_AUTO
                        status_callback(current=idx, done=False, state="AUTO")
                        self.set_mission_waypoint(self._last_reached_seq)
                        self.set_mode("AUTO")

            elif self.current_state == WaypointState.POSITIONING:
                if self.check_reposition_reached(
                    _alt=5, _lat=self._target_lat, _lon=self._target_lon
                ):
                    self.current_state = WaypointState.WAITING_DROP
                    status_callback(
                        current=self._last_reached_seq,
                        done=False,
                        state="DROPPING LOAD",
                    )
                    print("Positioning reached, waiting for drop...")

            elif self.current_state == WaypointState.WAITING_DROP:
                if drop_hook is not None and drop_hook():
                    self.current_state = WaypointState.WAITING_RAISE
                    status_callback(
                        current=self._last_reached_seq, done=False, state="RAISING LOAD"
                    )
                    print("Hook dropped, waiting for raise...")
                else:
                    # Skip hook operations, go back to auto
                    self.set_mission_waypoint(self._last_reached_seq)
                    self.set_mode("AUTO")
                    print("Skipping hook operations, returning to AUTO mode")
                    self.current_state = WaypointState.FLYING_AUTO
                    status_callback(
                        current=self._last_reached_seq, done=False, state="AUTO"
                    )

            elif self.current_state == WaypointState.WAITING_RAISE:
                if raise_hook is not None and raise_hook():
                    print("Hook operations completed")
                else:
                    print("Hook raise cancelled")

                # Resume auto flight
                self.set_mission_waypoint(self._last_reached_seq)
                self.set_mode("AUTO")
                status_callback(
                    current=self._last_reached_seq, done=False, state="AUTO"
                )
                self.current_state = WaypointState.FLYING_AUTO
            return False

        if timeout is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if func():
                    return True
        else:
            return func()
        self.log("Mission monitoring timed out", "error")
        return False


if __name__ == "__main__":
    connection = ArdupilotConnection("udp:127.0.0.1:14550")

    connection.arm()
    connection.takeoff(10)
    location = connection.get_relative_gps_location()
    if not location:
        exit(1)

    curr_lat, curr_lon, curr_alt = location
    mission = [
        [curr_lat + 0.00001, curr_lon + 0.00001, 3],
        [curr_lat - 0.00002, curr_lon - 0.00002, 3],
        [curr_lat + 0.00002, curr_lon + 0.00002, 3],
        [curr_lat - 0.00001, curr_lon + 0.00001, 3],
        [curr_lat + 0.00002, curr_lon + 0.00001, 3],
        [curr_lat + 0.00002, curr_lon - 0.00002, 3],
        [curr_lat, curr_lon, curr_alt + 3],  # Return to home
    ]

    # USING REPOSITION FOR MISSION WAYPOINTS
    # for waypoint in mission:
    # 	connection.goto_waypointv2(*waypoint)
    # 	while not connection.check_reposition_reached(*waypoint):
    # 		time.sleep(1)

    # USING MISSION UPLOAD FOR MISSION WAYPOINTS
    try:
        connection.upload_mission(
            [Waypoint(lat, lon, alt, hold=0) for lat, lon, alt in mission]
        )

        # THIS IS WRITTEN TO PROVE THAT
        # SANDWICHED BETWEEN MISSION WAYPOINTS,
        # THE DRONE CAN BE REPOSITIONED
        prev_seq = 0

        def _update_status_hook(seq, completed):
            # after waypoint is reached, set to GUIDED mode, move to base, and then set back to AUTO
            global prev_seq
            if not completed:
                connection.log(f"Current waypoint: {seq} {prev_seq}")
                if seq == prev_seq + 1:
                    connection.log(f"Reached waypoint {seq}, setting to GUIDED mode.")
                    connection.set_mode("GUIDED")
                    connection.goto_waypointv2(curr_lat, curr_lon, 10)
                    while not connection.check_reposition_reached(
                        curr_lat, curr_lon, 10
                    ):
                        time.sleep(1)
                    connection.log(
                        f"Waypoint {seq} reached, setting to AUTO mode.", "success"
                    )
                    connection.set_mode("AUTO")
                    prev_seq = seq

        connection.start_mission()
        while not connection.monitor_mission_progress(callback=_update_status_hook):
            time.sleep(1)
    except Exception as e:
        connection.log(f"Error during mission upload: {e}", "error")
    finally:
        connection.clear_mission()
        connection.return_to_launch()
        connection.close()
        connection.log("Connection closed.")
        connection.log("Ardupilot connection example completed.")
