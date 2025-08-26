import enum
import time
import traceback

from PySide6.QtCore import QObject, QTimer, Signal
from qfluentwidgets import MessageBox

from src.controls.mavlink import ardupilot, mission_types
from src.mq.crane import ZMQTopics
from src.mq.zmq_client import ZMQClient


class WaypointHoldState(enum.Enum):
    """Enum to hold the state of a waypoint hold action."""

    HOLD = "hold"
    START = "start"
    MOVING = "moving"


class DroneClient(QObject):
    """
    Mock drone client that will be replaced with actual implementation.
    """

    drone_status_update = Signal(dict)
    connection_status = Signal(bool, str)
    mission_progress = Signal(int, str)

    def __init__(
        self,
        logger=None,
    ):
        super().__init__()
        self.connected = False
        self.k_connected = False
        self._helipad_gps = None
        self._tank_gps = None  # (40.9589782, 29.1358378)
        self._status = None
        self.mission_waypoints = []
        self.current_waypoint_index = -1
        self.master_connection = None
        self.kamikaze_connection = None
        self.log = logger if logger is not None else print

        self.zmq_client = None

        # Setup status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.setInterval(500)  # Update every half second

        try:
            self._control_address = mission_types.get_control_address()
        except Exception as e:
            self.log(e)

    def drop_load(self):
        """Drop load command."""
        if self.master_connection is None:
            return False
        if self.zmq_client is None:
            self.log("server is not connected", "error")
            return False

        msg = self.zmq_client.send_command(ZMQTopics.DROP_LOAD.name)
        self.log(msg)
        return

    def pick_load(self):
        """Pick load command."""
        if self.master_connection is None:
            return False

        if self.zmq_client is None:
            self.log("server is not connected", "error")
            return False

        msg = self.zmq_client.send_command(ZMQTopics.PICK_LOAD.name)
        self.log(msg)
        return

    def fetch_helipad_gps(self) -> bool:
        """Fetch the helipad GPS coordinates."""
        if self.master_connection is None:
            return False
        if self.zmq_client is None:
            return False

        helipad_gps = self.zmq_client.send_command(ZMQTopics.HELIPAD_GPS.name)
        helipad_gps = (
            helipad_gps.split(">")[-1] if helipad_gps and ">" in helipad_gps else None
        )
        helipad_gps = helipad_gps.split(",") if helipad_gps else None
        if helipad_gps and len(helipad_gps) == 2:
            # print(f"Helipad GPS: {helipad_gps}")
            try:
                lat = float(helipad_gps[0])
                lon = float(helipad_gps[1])
                self._helipad_gps = (lat, lon)
                return True
            except ValueError:
                self.log("Invalid helipad GPS format")
                print("Invalid helipad GPS format")
                return False
        return False

    def fetch_tank_gps(self) -> bool:
        """Fetch the tank GPS coordinates."""
        if self.master_connection is None:
            return False
        if self.zmq_client is None:
            return False

        tank_gps = self.zmq_client.send_command(ZMQTopics.TANK_GPS.name)
        tank_gps = tank_gps.split(">")[-1] if tank_gps and ">" in tank_gps else None
        tank_gps = tank_gps.split(",") if tank_gps else None
        if tank_gps and len(tank_gps) == 2:
            try:
                lat = float(tank_gps[0])
                lon = float(tank_gps[1])
                self._tank_gps = (lat, lon)
                return True
            except ValueError:
                self.log("Invalid tank GPS format", "error")
        return False

    def raise_hook(self):
        """Raise hook command."""
        if self.master_connection is None:
            return False

        if self.zmq_client is None:
            return False
        msg = self.zmq_client.send_command(ZMQTopics.RAISE_HOOK.name)
        self.log(msg)
        return

    def drop_hook(self):
        """Drop hook command."""
        if self.master_connection is None:
            return False
        if self.zmq_client is None:
            return False

        msg = self.zmq_client.send_command(ZMQTopics.DROP_HOOK.name)
        self.log(msg)
        return

    def connect_to_drone(self, connection_string, is_kamikaze=False):
        """Connect to drone at the specified TCP address and port."""

        try:
            if is_kamikaze:
                self.kamikaze_connection = ardupilot.ArdupilotConnection(
                    connection_string, logger=self.log
                )
                self.k_connected = True
                self.kamikaze_connection.set_mode("GUIDED")
                # self.kamikaze_connection.wait_heartbeat()
            else:
                self.master_connection = ardupilot.ArdupilotConnection(
                    connection_string=connection_string,
                    logger=self.log,
                )
                self.connected = True
                self.master_connection.set_mode("GUIDED")

                # Start status updates
                self.log("Starting ZMQ client...")
                if connection_string.startswith("tcp:"):
                    address = connection_string[4:].split(":")[0]
                    # parse the connection string and get the ip
                    print("ZMQ ADDRESS: ", connection_string, address)
                    self.zmq_client = ZMQClient(
                        _logger=self.log,
                    )
                    self.zmq_client.connect()
                    self.log("ZMQ client started")
                self.log("Starting status timer...")
                self.status_timer.start()

            if not is_kamikaze:
                self.connection_status.emit(
                    True,
                    f"[MAVLink] Connected to {connection_string} for {'Kamikaze' if is_kamikaze else 'Drone'}",
                )

            # self.connection_status.emit(True, f"[MAVLink] Heartbeat from system {connection.target_system}, component {connection.target_component}")
            return True
        except:
            print(traceback.format_exc())
            return False

    def set_logger(self, logger):
        self.log = logger

    def close(self, is_kamikaze=False):
        """Disconnect from the drone."""

        if is_kamikaze and self.kamikaze_connection is not None:
            self.kamikaze_connection.close()
            self.kamikaze_connection = None
        elif self.master_connection is not None:
            self.master_connection.close()
            self.master_connection = None

            self.connected = False

            if self.zmq_client:
                self.zmq_client.stop()
            self.zmq_client = None
            self.status_timer.stop()

            self.connection_status.emit(
                False,
                "[MAVLink] Disconnecting from drone",
            )

    def arm(self, is_kamikaze=False):
        """Arm the drone."""
        try:
            if not self.connected:
                return False

            self.log("Arming drone...")
            if is_kamikaze:
                self.kamikaze_connection.arm()
            else:
                self.master_connection.arm()

            self.log("Drone armed successfully.")
            return True
        except:
            return False

    def disarm(self):
        """Disarm the drone."""
        if not self.connected:
            return False
        if not self._status:
            return False

        # Check if the drone is armed from the status update
        armed = self._status.get("armed", False)
        if not armed:
            self.log("Disarming a unarmed or not flying drone")
            return False
        self.log("Disarming drone...")
        self.master_connection.disarm()
        return True

    def takeoff(self, altitude):
        """Take off to the specified altitude."""
        armed = self._status.get("armed", False)
        if not self.connected or not armed:
            return False

        self.log("Taking off...")
        self.master_connection.takeoff(altitude, wait_time=0.1)
        return True

    def land(self):
        """Land the drone."""
        if not self.connected:
            return False

        self.master_connection.land()
        return True

    def return_to_home(self):
        """Return to launch location."""
        if not self.connected:
            return False

        self.master_connection.return_to_launch()
        return True

    def goto_coordinates(self, lat, lon, alt, relative=False):
        """Move to the specified coordinates."""
        # armed = self.status.get("armed", False)
        if relative:
            if not self._status.get("home", None):
                return False
            lat += self._status["home"]["lat"]
            lon += self._status["home"]["lon"]
        self.log(f"Moving to coordinates: {lat}, {lon}, {alt} (relative={relative})")

        self.master_connection.goto_waypointv2(lat, lon, alt)
        return True

    def upload_mission(self, waypoints):
        """Upload a mission with waypoints."""
        if not self.connected:
            return False

        self.mission_waypoints = waypoints
        self.master_connection.upload_mission(waypoints)
        return True

    def start_mission(self):
        """Start the uploaded mission."""
        if not self.mission_waypoints:
            return False

        self.current_waypoint_index = 1
        self.mission_completed = False

        self.master_connection.start_mission()
        self.mission_progress.emit(0, "Mission started")

        return True

    def cancel_mission(self):
        """Cancel the current mission."""
        self.master_connection.clear_mission()
        self.current_waypoint_index = -1
        self.mission_progress.emit(0, "Mission cancelled")
        return True

    def kamikaze(self):
        if not self.k_connected:
            self.log("Kamikaze connection not established")
            return False
        gps = self._tank_gps
        if gps is None:
            self.log("Target GPS not available", "error")
            return False
        self.kamikaze_connection.goto_kamikaze(lat=gps[0], lon=gps[1])
        self.log("Kamikaze mode activated", "success")
        return True

    def _update_status_hook(self, current, done, state="AUTO"):
        self.current_waypoint_index = current
        self.mission_completed = done
        msg = f"State: {state}"
        self.mission_progress.emit(
            int((current) * 100 / len(self.mission_waypoints)), msg
        )

    def _update_status(self):
        """Update and emit drone status information."""
        if self.master_connection is None:
            return
        status = self.master_connection.get_status()
        self.fetch_helipad_gps()
        self.fetch_tank_gps()

        if hasattr(self, "mission_completed"):
            # if self.master_connection.monitor_mission_progress(
            #     callback=self._update_status_hook
            # ):
            #     self.mission_progress.emit(100, "Mission completed")
            #     delattr(self, "mission_completed")

            def drop_hook():
                m = MessageBox(
                    "Drop Hook", "Drop hook?", MessageBox.Yes | MessageBox.No
                )
                reply = m.exec()
                if reply == MessageBox.Yes:
                    print("Dropping hook...")
                    return True
                return False

            def raise_hook():
                m = MessageBox(
                    "Raise Hook", "Raise hook?", MessageBox.Yes | MessageBox.No
                )
                reply = m.exec()
                if reply == MessageBox.Yes:
                    print("Raising hook...")
                    return True
                return False

            if self.master_connection.monitor_mission_progressv2(
                status_callback=self._update_status_hook,
                helipad_gps=self._helipad_gps,
                drop_hook=drop_hook,
                raise_hook=raise_hook,
            ):
                self.mission_progress.emit(100, "Mission completed")
                delattr(self, "mission_completed")
        else:
            self.mission_progress.emit(0, "Mission not started")

        status["helipad_gps"] = self._helipad_gps
        status["tank_gps"] = self._tank_gps
        if self.kamikaze_connection and self.k_connected:
            status[
                "kamikaze_gps"
            ] = self.kamikaze_connection.get_relative_gps_location()
        self.drone_status_update.emit(status)
        self._status = status
