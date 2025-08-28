import asyncio
import logging
import math
import time
from dataclasses import dataclass

import pymavlink.dialects.v20.all as dialect
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from pymavlink import mavutil

from src.controls.mavlink.mission_types import Waypoint


@dataclass
class WaypointState:
    FLYING_AUTO = "flying_auto"
    POSITIONING = "positioning"
    WAITING_DROP = "waiting_drop"
    WAITING_RAISE = "waiting_raise"


class Px4Connection:
    def __init__(self, connection_string, wait_heartbeat=10, logger=None):
        self.connection_string = connection_string
        self.target_system = 1
        self.target_component = 1
        self.master = System()
        connection_string = connection_string.replace("udpin:", "udpin://")
        print(connection_string)

        async def print_status_text(drone):
            try:
                async for status_text in drone.telemetry.status_text():
                    print(f"Status: {status_text.type}: {status_text.text}")
            except asyncio.CancelledError:
                return

        async def _setup():
            await self.master.connect(system_address=connection_string)
            self.status_text_task = asyncio.ensure_future(
                print_status_text(self.master)
            )

            print("Waiting for drone to connect...")
            async for state in self.master.core.connection_state():
                if state.is_connected:
                    print(f"-- Connected to drone!")
                    break

            print("Waiting for drone to have a global position estimate...")
            async for health in self.master.telemetry.health():
                if health.is_global_position_ok and health.is_home_position_ok:
                    print("-- Global position estimate OK")
                    break

        asyncio.run(_setup())

        # timeout for heartbeat
        if not self.master:
            raise ConnectionError(
                f"Failed to connect to {connection_string} within {wait_heartbeat} seconds"
            )

        self.log = self._set_logger(logger)
        self.log(
            f"Connected to {self.connection_string} with system ID {self.master.component_information.name}",
            "info",
        )

        self.current_state = WaypointState.FLYING_AUTO

        self.status = {
            "home": None,
            "mode": None,
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
        self.master.action_server.set_flight_mode(mode)
        mode_id = dict(
            ACRO=12,
            ALTCTL=10,
            FOLLOW_ME=8,
            HOLD=3,
            LAND=6,
            MANUAL=9,
            MISSION=4,
            OFFBOARD=7,
            POSCTL=11,
            READY=1,
            RETURN_TO_LAUNCH=5,
            STABILIZED=13,
            TAKEOFF=2,
            UNKNOWN=0,
        )[mode]
        self.master.action_server.set_flight_mode(mode_id)

    def get_mode(self):
        mode = asyncio.run(self.master.telemetry.flight_mode())
        return mode

    def fetch_home(self):
        # home = asyncio.run(self.master.telemetry.home())
        # return home
        pass

    def arm(self):
        """
        Arms the vehicle and sets it to GUIDED mode.
        """
        # Arm the vehicle
        self.log("Arming motors...", "info")
        asyncio.run(self.master.action.arm())

    def safety_switch(self, state):
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_DECODE_POSITION_SAFETY,
            1 if state else 0,
        )

    def disarm(self):
        """
        Disarms the vehicle.
        """
        self.log("Disarming motors...", "info")
        asyncio.run(self.master.action.disarm())
        self.log("Vehicle disarmed!", "info")

    def takeoff(self, target_altitude=5.0, wait_time=10):
        """
        Initiates takeoff to target altitude in meters.
        """
        self.log(f"Taking off to {target_altitude} meters...", "info")
        asyncio.run(self.master.action.takeoff(target_altitude))
        # Optional: wait for some time or monitor altitude via message stream
        time.sleep(wait_time)  # crude wait; replace with altitude monitor if needed
        self.log("Takeoff command sent.", "info")

    def return_to_launch(self):
        asyncio.run(self.master.action.return_to_launch())

    def land(self):
        self.log("Landing...", "info")
        asyncio.run(self.master.action.land())
        self.log("Landing command sent.", "info")

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

    def upload_mission(self, waypoints: list[Waypoint]):
        num_wp = len(waypoints)
        self.num_wp = num_wp
        mission_items = []
        for wp in waypoints:
            mission_items.append(
                MissionItem(
                    wp.lat,
                    wp.lon,
                    wp.alt,
                    wp.hold,
                    True,
                    float("nan"),
                    float("nan"),
                    MissionItem.CameraAction.NONE,
                    float("nan"),
                    float("nan"),
                    float("nan"),
                    float("nan"),
                    float("nan"),
                    MissionItem.VehicleAction.NONE,
                )
            )
        mission_plan = MissionPlan(mission_items)
        asyncio.run(self.master.mission.upload_mission(mission_plan))
        self.log("Mission upload complete.", "info")

    def clear_mission(self):
        # Clear mission
        self.log("Clearing all missions. Hack...", "info")
        asyncio.run(self.master.mission.clear_mission())
        return True

    def start_mission(self):
        asyncio.run(self.master.mission.start_mission())

    def get_relative_gps_location(self, timeout=1.0):
        """
        Blocking call to get the current GPS location.
        Returns: (latitude, longitude, relative_altitude)
        """

        async def _get_gps():
            try:
                async for pos in self.drone.telemetry.position():
                    return pos.latitude_deg, pos.longitude_deg, pos.relative_altitude_m
            except Exception:
                return None

        try:
            return asyncio.run(asyncio.wait_for(_get_gps(), timeout=timeout))
        except asyncio.TimeoutError:
            return None

    def get_relative_gps_location(self, timeout=1.0):
        """
        Blocking call to get the current GPS location.
        Returns: (latitude, longitude, relative_altitude)
        """

        async def _get_gps():
            try:
                async for pos in self.drone.telemetry.position():
                    return pos.latitude_deg, pos.longitude_deg, pos.absolute_altitude_m
            except Exception:
                return None

        try:
            return asyncio.run(asyncio.wait_for(_get_gps(), timeout=timeout))
        except asyncio.TimeoutError:
            return None

        return _lat, _lon, _ralt, _alt

    def get_current_attitude(self, timeout=1.0):
        """
        Blocking call to get the current attitude (roll, pitch, yaw) of the drone in radians.

        Returns:
            tuple: (roll, pitch, yaw) in radians
            None: if attitude data is not available within timeout
        """

        async def _get_attitude():
            try:
                async for att in self.drone.telemetry.attitude_euler():
                    roll = math.radians(att.roll_deg)
                    pitch = math.radians(att.pitch_deg)
                    yaw = math.radians(att.yaw_deg)
                    if yaw < 0:
                        yaw += 2 * math.pi
                    return roll, pitch, yaw
            except Exception:
                return None

        try:
            return asyncio.run(asyncio.wait_for(_get_attitude(), timeout=timeout))
        except asyncio.TimeoutError:
            return None

    async def _get_status(self):
        # HOME_POSITION
        try:
            async for home in self.master.telemetry.home():
                self.status["home"] = {
                    "lat": home.latitude_deg,
                    "lon": home.longitude_deg,
                    "alt": home.absolute_altitude_m,
                }
                break  # Only read once
        except Exception:
            pass

        # GLOBAL POSITION
        try:
            async for pos in self.master.telemetry.position():
                self.status["position"] = {
                    "lat": pos.latitude_deg,
                    "lon": pos.longitude_deg,
                    "alt": pos.relative_altitude_m,
                }
                break
        except Exception:
            pass

        # ATTITUDE
        try:
            async for attitude in self.master.telemetry.attitude_euler():
                self.status["orientation"] = {
                    "roll": math.degrees(attitude.roll_deg),
                    "pitch": math.degrees(attitude.pitch_deg),
                    "yaw": math.degrees(attitude.yaw_deg),
                }
                break
        except Exception:
            pass

        # VFR_HUD / Speed
        try:
            async for vfr in self.master.telemetry.velocity_ned():
                # Compute groundspeed from NED components
                gs = math.sqrt(vfr.north_m_s ** 2 + vfr.east_m_s ** 2)
                self.status["speed"] = gs
                break
        except Exception:
            pass

        # BATTERY
        try:
            async for battery in self.master.telemetry.battery():
                self.status["battery"] = battery.remaining_percent
                break
        except Exception:
            pass

        # ARMED & FLIGHT MODE
        try:
            async for armed_state in self.master.telemetry.armed():
                self.status["armed"] = armed_state
                break
        except Exception:
            pass

        try:
            async for flight_mode in self.master.telemetry.flight_mode():
                self.status["mode"] = flight_mode
                break
        except Exception:
            pass

        # MISSION CURRENT WAYPOINT
        try:
            async for mission_progress in self.master.mission.mission_progress():
                self.status["current_waypoint"] = mission_progress.current
                self.status["total_waypoints"] = mission_progress.total
                self.status["mission_active"] = mission_progress.current > 0
                break
        except Exception:
            pass

        # FLYING STATUS
        self.status["flying"] = (
            self.status["armed"] and self.status["mode"] != "STABILIZE"
        )

        return

    def get_status(self):
        asyncio.run(self._get_status())
        return

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

    def set_mission_waypoint(self, wp: int):
        return self.master.mav.mission_set_current_send(
            self.master.target_system, self.master.target_component, wp
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

                # TODO: set state for initial condition. for idx=0. drop and raise hook but no stabilization
                if reached and idx > 1:
                    print(
                        f"{reached=}   {idx=} {self.num_wp - 1} {self._last_reached_seq}"
                    )
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

    def close(self):
        self.master.close()
        delattr(self, "master")
        self.log("Mavlink Connection closed.", "info")


if __name__ == "__main__":
    connection = Px4Connection("udpin:127.0.0.1:14550")

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
