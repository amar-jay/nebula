import json
import sys
import time

from pymavlink import mavutil
from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPalette,
    QPixmap,
    QTransform,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTabBar,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
)
from qfluentwidgets import RoundMenu as QMenu
from qfluentwidgets import BodyLabel as QLabel
from qfluentwidgets import CheckBox as QCheckBox
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    LineEdit as QLineEdit,  # MessageBox as QMessageBox,; DoubleSpinBox as QDoubleSpinBox,; HeaderCardWidget as QGroupBox,; ProgressBar as QProgressBar,
)
from qfluentwidgets import (
    MessageBox,
)
from qfluentwidgets import PrimaryPushButton as _PrimaryPushButton
from qfluentwidgets import PushButton as QPushButton
from qfluentwidgets import SpinBox as QSpinBox
from qfluentwidgets import TableWidget as QTableWidget
from qfluentwidgets import TextEdit as QTextEdit
from qfluentwidgets import (
    Theme,
    setTheme,
    setThemeColor,
)

from src.controls.mavlink import ardupilot
from src.controls.mavlink.mission_types import Waypoint
from src.mq.messages import ZMQTopics
from src.mq.zmq_client import ZMQClient
from src.new_control_station.src.camera.camera_widget import CameraWidget
from src.new_control_station.src.horizon.attitude_widget import AttitudeIndicator
from src.new_control_station.src.horizon.compass_widget import CompassWidget
from src.new_control_station.src.horizon.guage_widget import (
    AltitudeGauge,
    BatteryGauge,
    SpeedGauge,
)
from src.new_control_station.src.map.map_widget import MapWidget


def PrimaryPushButton(text):
    btn = _PrimaryPushButton(text)
    style_sheet = btn.styleSheet()
    # set width to fit text
    style_sheet += "\nPrimaryPushButton {min-width: 50px; padding: 5px 10px;}"
    btn.setStyleSheet(style_sheet)
    return btn


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
        self.initial_position = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
        self.k_current_position = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
        self.mission_waypoints = []
        self.current_waypoint_index = -1
        self.master_connection = None
        self.kamikaze_connection = None
        self.log = logger

        self.zmq_client = ZMQClient()

        # Setup status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.setInterval(1000)  # Update every second

    def drop_load(self):
        """Drop load command."""
        if self.master_connection is None:
            return False

        msg = self.zmq_client.send_command(ZMQTopics.DROP_LOAD)
        self.log(msg)
        return

    def pick_load(self):
        """Pick load command."""
        if self.master_connection is None:
            return False

        msg = self.zmq_client.send_command(ZMQTopics.PICK_LOAD)
        self.log(msg)
        return

    def raise_hook(self):
        """Raise hook command."""
        if self.master_connection is None:
            return False

        msg = self.zmq_client.send_command(ZMQTopics.RAISE_HOOK)
        self.log(msg)
        return

    def drop_hook(self):
        """Drop hook command."""
        if self.master_connection is None:
            return False

        msg = self.zmq_client.send_command(ZMQTopics.DROP_HOOK)
        self.log(msg)
        return

    def connect_to_drone(self, connection_string, is_kamikaze=False):
        """Connect to drone at the specified TCP address and port."""

        # if connection_string.startswith("udp:") or connection_string.startswith("tcp:"):
        # address, port = connection_string[4:].split(":")
        # port = int(port)

        if is_kamikaze:
            self.kamikaze_connection = ardupilot.ArdupilotConnection(connection_string, logger=self.log)
            self.k_connected = True
            self.kamikaze_connection.set_mode("GUIDED")
            # self.kamikaze_connection.wait_heartbeat()
        else:
            self.master_connection = ardupilot.ArdupilotConnection(
                connection_string=connection_string,
                logger= self.log,
                # world="delivery_runway",
                # model_name="iris_with_stationary_gimbal",
                # camera_link="tilt_link",
                # logger=lambda *message: self.log(
                # f"[MAVLink] {' '.join(map(str, message))}",
                # ),
            )
            self.master_connection.set_mode("GUIDED")
            self.connected = True

        # Start status updates
        self.log("Starting ZMQ client...")
        self.zmq_client.start()
        self.log("ZMQ client started")
        self.log("Starting status timer...")
        self.status_timer.start()

        if is_kamikaze:
            location = self.kamikaze_connection.get_current_gps_location()
            if location is not None:
                lat, lon, alt = location
                self.k_current_position = {"lat": lat, "lon": lon, "alt": alt}
        else:
            location = self.master_connection.get_current_gps_location()
            if location is not None:
                lat, lon, alt = location
                self.initial_position = {"lat": lat, "lon": lon, "alt": alt}

        self.connection_status.emit(
            True,
            f"[MAVLink] Connected to {connection_string} for {'Kamikaze' if is_kamikaze else 'Drone'}",
        )

        # self.connection_status.emit(True, f"[MAVLink] Heartbeat from system {connection.target_system}, component {connection.target_component}")
        return True

    def set_logger(self, logger):
        self.log = logger

    def disconnect(self, is_kamikaze=False):
        """Disconnect from the drone."""

        if is_kamikaze and self.kamikaze_connection is not None:
            self.kamikaze_connection.close()
            self.kamikaze_connection = None
        elif self.master_connection is not None:
            self.master_connection.close()
            self.master_connection = None

        self.connected = False

        self.zmq_client.stop()
        self.status_timer.stop()

        self.connection_status.emit(
            False,
            f"[MAVLink] Disconnecting from drone",
        )

    def arm(self, is_kamikaze=False):
        """Arm the drone."""
        if not self.connected:
            return False

        self.log("Arming drone...")
        if is_kamikaze:
            self.kamikaze_connection.arm()
        else:
            self.master_connection.arm()

        self.log("Drone armed successfully.")
        return True

    def disarm(self):
        """Disarm the drone."""
        if not self.connected:
            return False

        # Check if the drone is armed from the status update
        armed = self.status.get("armed", False)
        if not armed:
            self.log("Disarming a unarmed or not flying drone")
            return False
        self.log("Disarming drone...")
        self.master_connection.disarm()
        return True

    def takeoff(self, altitude):
        """Take off to the specified altitude."""
        armed = self.status.get("armed", False)
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
            lat += self.initial_position["lat"]
            lon += self.initial_position["lon"]
        self.log(f"Moving to coordinates: {lat}, {lon}, {alt} (relative={relative})")
        self.log(f"Initial position: {self.initial_position}")

        self.master_connection.goto_waypointv2(lat, lon, alt)

        self.initial_position = {"lat": lat, "lon": lon, "alt": alt}
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

        self.current_waypoint_index = 0
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

    def _update_status_hook(self, current, done):
        self.current_waypoint_index = current
        self.mission_completed = done
        msg = f"Moving to waypoint {current}/{len(self.mission_waypoints)}"
        self.mission_progress.emit(
            int((current) * 100 / len(self.mission_waypoints)), msg
        )

    def _update_status(self):
        """Update and emit drone status information."""
        status = self.master_connection.get_status()

        if hasattr(self, "mission_completed"):
            if self.master_connection.monitor_mission_progress(
                _update_status_hook=self._update_status_hook
            ):
                self.mission.progress.emit(100, "Mission completed")
                delattr(self, "mission_completed")
        else:
            self.mission_progress.emit(0, "Mission not started")

        self.drone_status_update.emit(status)
        self.status = status


class MissionWaypointTable(QTableWidget):
    """
    Table widget for displaying and editing mission waypoints.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(
            ["#", "Latitude", "Longitude", "Altitude (m)", "Hold", "Auto", "Actions"]
        )
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.DoubleClicked)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)

    def add_waypoint(self, index, lat, lon, alt, hold=10, auto=True):
        """Add a new waypoint to the table."""
        row = self.rowCount()
        self.insertRow(row)

        # Add waypoint data
        self.setItem(row, 0, QTableWidgetItem(str(index)))
        self.setItem(row, 1, QTableWidgetItem(str(lat)))
        self.setItem(row, 2, QTableWidgetItem(str(lon)))
        self.setItem(row, 3, QTableWidgetItem(str(alt)))
        self.setItem(row, 4, QTableWidgetItem(str(hold)))

        # Add checkbox for Auto
        auto_checkbox = QCheckBox()
        auto_checkbox.setChecked(auto)
        auto_widget = QWidget()
        auto_layout = QHBoxLayout(auto_widget)
        auto_layout.addWidget(auto_checkbox)
        auto_layout.setAlignment(auto_checkbox, Qt.AlignCenter)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        self.setCellWidget(row, 5, auto_widget)

        # Add delete button
        delete_btn = QPushButton("❌")
        delete_btn.setStyleSheet("margin: 0px;")
        delete_btn.clicked.connect(
            lambda: self.removeRow(self.indexAt(delete_btn.pos()).row())
        )
        self.setCellWidget(row, 6, delete_btn)

    def clear_waypoints(self):
        """Clear all waypoints from the table."""
        self.setRowCount(0)

    def get_waypoints(self):
        """Get all waypoints from the table."""
        waypoints = []
        for row in range(self.rowCount()):
            auto_widget = self.cellWidget(row, 5)
            auto_checkbox = auto_widget.findChild(QCheckBox)
            waypoint = Waypoint(
                lat=float(self.item(row, 1).text()),
                lon=float(self.item(row, 2).text()),
                alt=float(self.item(row, 3).text()),
                hold=int(self.item(row, 4).text()),
                auto=auto_checkbox.isChecked(),
            )
            waypoints.append(waypoint)
        return waypoints


class ConsoleOutput(QTextEdit):
    """
    Widget for displaying console output.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

        # Set a dark background for the console
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.Text, QColor(200, 200, 200))
        self.setPalette(palette)

    def append_message(self, message, level="info"):
        """
        Append a message to the console.
        level can be "info", "success", "warning", or "error"
        """
        color_map = {
            "info": "#FFFFFF",
            "success": "#00FF00",
            "warning": "#FFFF00",
            "error": "#FF0000",
        }
        color = color_map.get(level, "#FFFFFF")

        timestamp = QApplication.instance().property("timestamp_fn")()
        self.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')


class DroneControlApp(QMainWindow):
    """
    Main application window for drone control.
    """

    def __init__(self):
        super().__init__()

        # Set application properties
        QApplication.instance().setProperty("timestamp_fn", self._get_timestamp)

        # Initialize drone client
        self.drone_client = DroneClient()

        # Initialize UI components
        self._init_ui()
        self.drone_client.set_logger(self.console.append_message)

        self.drone_client.connection_status.connect(self._on_connection_status_changed)
        self.drone_client.drone_status_update.connect(self._on_drone_status_update)
        self.drone_client.mission_progress.connect(self._on_mission_progress)

        # Set window properties
        self.setWindowTitle("MATEK Drone Control Center")

        # Log application start
        self.console.append_message("Drone Control Center started", "info")
        self.drone_client.set_logger(self.console.append_message)

    def _init_ui(self):
        """Initialize the UI components."""
        setTheme(Theme.DARK)
        setThemeColor("#0078d4", save=True)
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Create connection controls
        connection_group = QGroupBox("Connection")
        connection_layout = QVBoxLayout(connection_group)
        main_connection_group = QGroupBox("Drone")
        main_connection_layout = QHBoxLayout(main_connection_group)
        kamikaze_connection_group = QGroupBox("Kamikaze")
        kamikaze_connection_layout = QHBoxLayout(kamikaze_connection_group)

        self.tcp_address_input = QLineEdit()
        self.tcp_address_input.setText("127.0.0.1")
        self.tcp_address_input.setToolTip("Enter the drone's IP address")
        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(14550)
        self.tcp_port_input.setSingleStep(1000)

        self.connect_btn = PrimaryPushButton("Connect")
        self.connect_btn.clicked.connect(lambda: self._on_connect_clicked())
        self.connect_menu = QMenu("Connect", self)
        self.connect_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "Standard Connect",
                triggered=lambda: self._on_connect_clicked(),
            )
        )
        # self.connect_action.triggered.connect(lambda: self._on_connect_clicked())
        self.tcp_connect_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "TCP Connect",
                triggered=lambda: self._on_connect_clicked(_type="tcp"),
            )
        )
        self.connect_auto_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "Serial (/dev/ttyAMA0)",
                triggered=lambda: self._on_usb_connect_clicked(
                    connection_string="/dev/ttyAMA0"
                ),
            )
        )
        self.connect_sitl_action = self.connect_menu.addAction(
            Action(
                FIF.CONNECT,
                "USB (/dev/ttyUSB0)",
                triggered=lambda: self._on_usb_connect_clicked(
                    connection_string="/dev/ttyUSB0"
                ),
            )
        )
        self.connect_btn.setMenu(self.connect_menu)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)

        self.k_tcp_address_input = QLineEdit()
        self.k_tcp_address_input.setPlaceholderText("127.0.0.1")
        self.k_tcp_address_input.setToolTip("Enter the kamikaze drone's IP address")
        self.k_tcp_port_input = QSpinBox()
        self.k_tcp_port_input.setRange(1, 65535)
        self.k_tcp_port_input.setValue(14560)

        self.k_connect_btn = QPushButton("Connect")
        self.k_connect_btn.clicked.connect(self._on_connect_clicked)

        self.k_disconnect_btn = QPushButton("Disconnect")
        self.k_disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.k_disconnect_btn.setEnabled(False)

        self.map_btn_group = QGroupBox("Map Controls")
        map_btn_layout = QHBoxLayout(self.map_btn_group)

        move_marker_btn = QPushButton("Move Marker")
        move_marker_btn.clicked.connect(lambda: self.map_event("move_marker"))
        select_area_btn = QPushButton("Select Area")
        select_area_btn.clicked.connect(lambda: self.map_event("select_area"))
        select_waypoint = QPushButton("Set Waypoint")
        select_waypoint.clicked.connect(lambda: self.map_event("set_waypoint"))
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: self.map_event("clear_all"))
        sync_btn = PrimaryPushButton("Sync")
        sync_btn.clicked.connect(lambda: self.map_event("sync"))

        map_btn_layout.addWidget(move_marker_btn)
        map_btn_layout.addWidget(select_area_btn)
        map_btn_layout.addWidget(select_waypoint)
        map_btn_layout.addWidget(clear_all_btn)
        map_btn_layout.addWidget(sync_btn)

        connection_layout.addWidget(main_connection_group)
        connection_layout.addWidget(kamikaze_connection_group)

        main_connection_layout.addWidget(QLabel("IP"))
        main_connection_layout.addWidget(self.tcp_address_input)
        main_connection_layout.addWidget(QLabel("Port"))
        main_connection_layout.addWidget(self.tcp_port_input)
        main_connection_layout.addWidget(self.connect_btn)
        main_connection_layout.addWidget(self.disconnect_btn)

        kamikaze_connection_layout.addWidget(QLabel("IP"))
        kamikaze_connection_layout.addWidget(self.k_tcp_address_input)
        kamikaze_connection_layout.addWidget(QLabel("Port"))
        kamikaze_connection_layout.addWidget(self.k_tcp_port_input)
        kamikaze_connection_layout.addWidget(self.k_connect_btn)
        kamikaze_connection_layout.addWidget(self.k_disconnect_btn)

        # Create tab widget for different control panels
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setStyleSheet(
            """
		QTabWidget {
			min-width: 1000px;
			}
		QTabWidget::pane {
		    border-radius: 10px;
			padding: 0px;
		    margin-left: 15px;
		}

		QTabBar::tab:left {
		    background-color: #404040;
		    color: #ffffff;
		    border-radius: 6px;
		    min-height: 20px;
		    max-height: 100px;
		    min-width: 30px;
		    font-size: 8pt;
		    margin-top: 2px;
		    margin-bottom: 2px;
		}

		QTabBar::tab:selected {
			border-right: 2px solid #0078d4;
		}

		QTabBar::tab:hover:!selected {
			color: white;
		}

		QTabWidget::tab-bar {
		    alignment: center;
		    left: 5px;
		    top: 5px;
		}
		"""
        )

        # Basic controls tab
        basic_control_widget = QWidget()
        basic_control_layout = QVBoxLayout(basic_control_widget)

        controller_group = QGroupBox("Controller Controls")
        controller_layout = QHBoxLayout(controller_group)

        controller_row = QHBoxLayout()
        # drop load
        self.drop_load_btn = QPushButton("Drop Load")
        self.drop_load_btn.clicked.connect(self.drone_client.drop_load)
        # pick load
        self.pick_load_btn = QPushButton("Pick Load")
        self.pick_load_btn.clicked.connect(self.drone_client.pick_load)
        # raise hook
        self.raise_hook_btn = QPushButton("Raise Hook")
        self.raise_hook_btn.clicked.connect(self.drone_client.raise_hook)
        # drop hook
        self.drop_hook_btn = QPushButton("Drop Hook")
        self.drop_hook_btn.clicked.connect(self.drone_client.drop_hook)
        # kamikaze - red
        self.kamikaze_btn = PrimaryPushButton("Kamikaze")
        style_sheet = self.kamikaze_btn.styleSheet()
        style_sheet += "\nPrimaryPushButton {background-color: #B22222; color: white; border: 1px solid red;}\nPrimaryPushButton::hover {background-color: #B22222; color: white; border: 1px solid red;}"
        self.kamikaze_btn.setStyleSheet(style_sheet)

        controller_row.addWidget(self.drop_load_btn)
        controller_row.addWidget(self.pick_load_btn)
        controller_row.addWidget(self.raise_hook_btn)
        controller_row.addWidget(self.drop_hook_btn)
        controller_row.addWidget(self.kamikaze_btn)
        controller_layout.addLayout(controller_row)

        # Create drone control buttons
        control_group = QGroupBox("Drone Controls")
        control_layout = QVBoxLayout(control_group)

        # First row of controls
        controls_row1 = QHBoxLayout()

        self.arm_btn = PrimaryPushButton("Arm")
        self.arm_btn.clicked.connect(self._on_arm_clicked)
        self.arm_btn.setEnabled(False)

        self.disarm_btn = PrimaryPushButton("Disarm")
        self.disarm_btn.clicked.connect(self._on_disarm_clicked)
        self.disarm_btn.setEnabled(False)

        self.safety_btn = QCheckBox("Safety Switch")
        self.safety_btn.setChecked(False)
        self.safety_btn.stateChanged.connect(self._on_safety_clicked)
        self.safety_btn.setEnabled(False)

        self.takeoff_btn = QPushButton("Takeoff")
        self.takeoff_btn.clicked.connect(self._on_takeoff_clicked)
        self.takeoff_btn.setEnabled(False)

        self.land_btn = QPushButton("Land")
        self.land_btn.clicked.connect(self._on_land_clicked)
        self.land_btn.setEnabled(False)

        self.rtl_btn = QPushButton("Return to Home")
        self.rtl_btn.clicked.connect(self._on_rtl_clicked)
        self.rtl_btn.setEnabled(False)

        controls_row1.addWidget(self.arm_btn)
        controls_row1.addWidget(self.disarm_btn)
        controls_row1.addWidget(self.takeoff_btn)
        controls_row1.addWidget(self.land_btn)
        controls_row1.addWidget(self.rtl_btn)

        # Second row for goto controls
        goto_group = QGroupBox("Go to Position")
        goto_layout = QHBoxLayout(goto_group)

        self.goto_lat_input = QDoubleSpinBox()
        self.goto_lat_input.setRange(-90, 90)
        self.goto_lat_input.setDecimals(7)
        self.goto_lat_input.setSingleStep(0.0001)

        self.goto_lon_input = QDoubleSpinBox()
        self.goto_lon_input.setRange(-180, 180)
        self.goto_lon_input.setDecimals(7)
        self.goto_lon_input.setSingleStep(0.0001)

        self.goto_alt_input = QDoubleSpinBox()
        self.goto_alt_input.setRange(0, 500)
        self.goto_alt_input.setDecimals(1)
        self.goto_alt_input.setSingleStep(1.0)
        self.goto_alt_input.setValue(5.0)

        self.goto_btn = PrimaryPushButton("Go")
        self.goto_btn.clicked.connect(self._on_goto_clicked)
        self.goto_btn.setEnabled(False)

        self.open_map_btn = PrimaryPushButton("Open Map")
        self.open_map_btn.clicked.connect(self._on_open_map_clicked)

        goto_layout.addWidget(QLabel("Latitude:"))
        goto_layout.addWidget(self.goto_lat_input)
        goto_layout.addWidget(QLabel("Longitude:"))
        goto_layout.addWidget(self.goto_lon_input)
        goto_layout.addWidget(QLabel("Altitude (m):"))
        goto_layout.addWidget(self.goto_alt_input)
        goto_layout.addWidget(self.goto_btn)
        goto_layout.addWidget(self.open_map_btn)

        # Add takeoff altitude spinner
        takeoff_layout = QHBoxLayout()
        takeoff_layout.addWidget(self.safety_btn)
        takeoff_layout.addStretch()
        takeoff_layout.addWidget(QLabel("Takeoff Altitude (m):"))
        # add spacer
        self.takeoff_alt_input = QDoubleSpinBox()
        self.takeoff_alt_input.setRange(1, 100)
        self.takeoff_alt_input.setValue(5.0)
        takeoff_layout.addWidget(self.takeoff_alt_input)

        # Add all controls to the layout
        control_layout.addLayout(controls_row1)
        control_layout.addLayout(takeoff_layout)
        basic_control_layout.addWidget(self.map_btn_group)
        basic_control_layout.addWidget(control_group)
        basic_control_layout.addWidget(goto_group)
        basic_control_layout.addWidget(controller_group)

        # Create status display
        status_group = QGroupBox("Drone Status")
        status_layout = QGridLayout(status_group)

        self.connection_status_label = QLabel("Not Connected")
        self.armed_status_label = QLabel("Disarmed")
        self.flight_status_label = QLabel("Not Flying")
        self.position_label = QLabel("N/A")
        self.altitude_label = QLabel("N/A")
        self.orientation_label = QLabel("N/A")
        self.mode_label = QLabel("N/A")
        self.mode_label.setStyleSheet("color: #0078d4;")
        self.battery_progress = QProgressBar()
        self.battery_progress.setRange(0, 100)

        # Add status widgets to grid
        status_layout.addWidget(QLabel("Connection:"), 0, 0)
        status_layout.addWidget(self.connection_status_label, 0, 1)
        status_layout.addWidget(QLabel("Armed:"), 0, 2)
        status_layout.addWidget(self.armed_status_label, 0, 3)

        status_layout.addWidget(QLabel("Flight:"), 1, 0)
        status_layout.addWidget(self.flight_status_label, 1, 1)
        status_layout.addWidget(QLabel("Altitude:"), 1, 2)
        status_layout.addWidget(self.altitude_label, 1, 3)

        status_layout.addWidget(QLabel("Orientation:"), 2, 0)
        status_layout.addWidget(self.orientation_label, 2, 1)
        status_layout.addWidget(QLabel("Position:"), 2, 2)
        status_layout.addWidget(self.position_label, 2, 3)
        _label = QLabel("Mode:")
        _label.setStyleSheet("color: #0078d4;")
        status_layout.addWidget(_label, 3, 0)
        status_layout.addWidget(self.mode_label, 3, 1)
        status_layout.addWidget(QLabel("Battery:"), 3, 2)
        status_layout.addWidget(self.battery_progress, 3, 3, 1, 2)

        # Add status group to basic control layout
        basic_control_layout.addWidget(status_group)
        basic_control_layout.addStretch(1)

        # camera display tab
        camera_widget = CameraWidget(
            parent=self, video_client=self.drone_client.zmq_client
        )

        # Mission planning tab
        mission_widget = QWidget()
        mission_layout = QVBoxLayout(mission_widget)

        # Mission waypoints table
        mission_layout.addWidget(QLabel("Mission Waypoints:"))
        self.waypoint_table = MissionWaypointTable()
        mission_layout.addWidget(self.waypoint_table)

        # Add waypoint controls
        add_waypoint_group = QGroupBox("Add Waypoint")
        add_waypoint_layout = QHBoxLayout(add_waypoint_group)

        self.waypoint_lat_input = QDoubleSpinBox()
        self.waypoint_lat_input.setRange(-90, 90)
        self.waypoint_lat_input.setDecimals(7)
        self.waypoint_lat_input.setSingleStep(0.0001)

        self.waypoint_lon_input = QDoubleSpinBox()
        self.waypoint_lon_input.setRange(-180, 180)
        self.waypoint_lon_input.setDecimals(7)
        self.waypoint_lon_input.setSingleStep(0.0001)

        self.waypoint_alt_input = QDoubleSpinBox()
        self.waypoint_alt_input.setRange(0, 500)
        self.waypoint_alt_input.setDecimals(1)
        self.waypoint_alt_input.setSingleStep(1.0)
        self.waypoint_alt_input.setValue(10.0)

        self.waypoint_hold_input = QDoubleSpinBox()
        self.waypoint_hold_input.setRange(0, 60)
        self.waypoint_hold_input.setValue(10)
        self.waypoint_hold_input.setSingleStep(1)

        self.add_waypoint_btn = QPushButton("Add")
        self.add_waypoint_btn.clicked.connect(self._on_add_waypoint_clicked)

        add_waypoint_layout.addWidget(QLabel("Latitude:"))
        add_waypoint_layout.addWidget(self.waypoint_lat_input)
        add_waypoint_layout.addWidget(QLabel("Longitude:"))
        add_waypoint_layout.addWidget(self.waypoint_lon_input)
        add_waypoint_layout.addWidget(QLabel("Altitude (m):"))
        add_waypoint_layout.addWidget(self.waypoint_alt_input)
        add_waypoint_layout.addWidget(QLabel("Hold (s):"))
        add_waypoint_layout.addWidget(self.waypoint_hold_input)
        add_waypoint_layout.addWidget(self.add_waypoint_btn)

        # Mission file operations
        mission_file_layout = QHBoxLayout()

        self.load_mission_btn = QPushButton("Load Mission")
        self.load_mission_btn.clicked.connect(self._on_load_mission_clicked)

        self.save_mission_btn = QPushButton("Save Mission")
        self.save_mission_btn.clicked.connect(self._on_save_mission_clicked)

        self.clear_mission_btn = QPushButton("Clear Mission")
        self.clear_mission_btn.clicked.connect(self._on_clear_mission_clicked)

        mission_file_layout.addWidget(self.load_mission_btn)
        mission_file_layout.addWidget(self.save_mission_btn)
        mission_file_layout.addWidget(self.clear_mission_btn)
        mission_file_layout.addStretch()

        # Mission execution controls
        mission_exec_layout = QHBoxLayout()

        self.upload_mission_btn = QPushButton("Upload Mission")
        self.upload_mission_btn.clicked.connect(self._on_upload_mission_clicked)
        self.upload_mission_btn.setEnabled(False)

        self.start_mission_btn = QPushButton("Start Mission")
        self.start_mission_btn.clicked.connect(self._on_start_mission_clicked)
        self.start_mission_btn.setEnabled(False)

        self.cancel_mission_btn = QPushButton("Cancel Mission")
        self.cancel_mission_btn.clicked.connect(self._on_cancel_mission_clicked)
        self.cancel_mission_btn.setEnabled(False)

        mission_exec_layout.addWidget(self.upload_mission_btn)
        mission_exec_layout.addWidget(self.start_mission_btn)
        mission_exec_layout.addWidget(self.cancel_mission_btn)
        mission_exec_layout.addStretch()

        # Mission progress
        mission_progress_layout = QHBoxLayout()
        mission_progress_layout.addWidget(QLabel("Mission Progress:"))
        self.mission_progress_bar = QProgressBar()
        self.mission_progress_bar.setRange(0, 100)
        mission_progress_layout.addWidget(self.mission_progress_bar)
        self.mission_status_label = QLabel("No mission active")
        mission_progress_layout.addWidget(self.mission_status_label)

        # Add mission controls to the layout
        mission_layout.addWidget(add_waypoint_group)
        mission_layout.addLayout(mission_file_layout)
        mission_layout.addLayout(mission_exec_layout)
        mission_layout.addLayout(mission_progress_layout)

        telemetry_widget = QWidget()
        telemetry_layout = QHBoxLayout(telemetry_widget)
        telemetry_layout.setSpacing(20)
        telemetry_layout.setContentsMargins(20, 20, 20, 20)

        # Telemetry display
        attitudes = QVBoxLayout()
        guages = QVBoxLayout()
        self.attitude_indicator = AttitudeIndicator()
        self.battery_gauge = BatteryGauge()
        self.altitude_gauge = AltitudeGauge()
        self.speed_gauge = SpeedGauge()
        self.compass_widget = CompassWidget()

        guages.addWidget(self.battery_gauge)
        guages.addWidget(self.altitude_gauge)
        guages.addWidget(self.speed_gauge)

        attitudes.addWidget(self.attitude_indicator)
        attitudes.addWidget(self.compass_widget)

        telemetry_layout.addLayout(attitudes)
        telemetry_layout.addLayout(guages)

        # Console output tab
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)

        console_layout.addWidget(QLabel("Console Output:"))
        self.console = ConsoleOutput()
        console_layout.addWidget(self.console)

        # Add tabs to the tab widget
        self._create_tab(
            "src/new_control_station/assets/images/controls.png",
            "Controls",
            basic_control_widget,
        )
        self._create_tab(
            "src/new_control_station/assets/images/camera.png", "Camera", camera_widget
        )
        self._create_tab(
            "src/new_control_station/assets/images/mission.png",
            "Missions",
            mission_widget,
        )
        self._create_tab(
            "src/new_control_station/assets/images/telemetry.png",
            "Telemetry",
            telemetry_widget,
        )

        # self.tab_widget.addTab(mission_widget, "Mission Planning")
        self._create_tab(
            "src/new_control_station/assets/images/console.png",
            "‍Console",
            console_widget,
        )
        # self.tab_widget.addTab(console_widget, "Console")

        # Add widgets to main layout
        main_layout.addWidget(connection_group)
        main_layout.addWidget(self.tab_widget)

        # Set central widget
        self.setCentralWidget(main_widget)

        # Create dock widget
        self.dock = QDockWidget("Map Dock(Fullscreen Only)", self)
        canberra_airport = [-35.363261, 149.165230]
        self.dock_content = MapWidget(canberra_airport)
        self.dock_content.addMissionCallback(self.waypoint_table.add_waypoint)
        self.dock_content.clearMissionCallback(self.waypoint_table.clear_waypoints)
        self.dock_content.addPositionCallback(
            lambda lat, lon: self.goto_lat_input.setValue(lat)
            or self.goto_lon_input.setValue(lon)
        )
        self.dock.setWidget(self.dock_content)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetVerticalTitleBar
        )
        # set to full width
        self.dock.setMinimumWidth(800)
        # minimum height should be fullscreen height
        self.dock.setMinimumHeight(1000)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        # Initially hide the dock widget
        self.dock.setVisible(False)

        # Create the event filter to track window state changes
        self.installEventFilter(self)

    def _create_tab(self, icon_path, tooltip, widget):
        index = self.tab_widget.addTab(widget, "")  # Add empty tab
        # Create a rotated and centered QLabel as icon
        pixmap = QPixmap(icon_path)
        transform = QTransform().rotate(0)
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        icon_label = QLabel()
        icon_label.setPixmap(
            rotated_pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(40, 40)  # Ensure it's nicely contained
        self.tab_widget.setTabToolTip(index, tooltip)
        self.tab_widget.tabBar().setTabText(index, "")  # Remove text
        self.tab_widget.tabBar().setTabButton(
            index, QTabBar.ButtonPosition.LeftSide, icon_label
        )

    def _get_timestamp(self):
        """Get a formatted timestamp for console messages."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    def _on_connect_clicked(self, _type="udp"):
        """Handle connect button click."""
        address = self.tcp_address_input.text()
        port = self.tcp_port_input.value()

        if not address:
            self._show_error("Please enter a valid TCP address")
            return

        self.console.append_message(f"Connecting to {_type}:{address}:{port}", "info")
        connection_string = f"{_type}:{address}:{port}"
        if self.drone_client.connect_to_drone(connection_string):
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.arm_btn.setEnabled(True)
            self.safety_btn.setEnabled(True)
            self.upload_mission_btn.setEnabled(True)
            self.console.append_message(f"Connected to {address}:{port}", "success")
            # Set home marker on the map
            pose = self.drone_client.initial_position
            self.dock_content.set_home_marker(pose["lat"], pose["lon"])
        else:
            self._show_error(f"Failed to connect to {address}:{port}")
            self.console.append_message(
                f"Failed to connect to {address}:{port}", "error"
            )

    def _on_usb_connect_clicked(self, connection_string="/dev/ttyUSB0"):
        """Handle connect button click."""

        self.console.append_message(f"Connecting to {connection_string}...", "info")
        if self.drone_client.connect_to_drone(connection_string):
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.arm_btn.setEnabled(True)
            self.safety_btn.setEnabled(True)
            self.upload_mission_btn.setEnabled(True)
            self.console.append_message(f"Connected to {connection_string}", "success")
        else:
            self._show_error(f"Failed to connect to {connection_string}")
            self.console.append_message(
                f"Failed to connect to {connection_string}", "error"
            )

    def _on_disconnect_clicked(self):
        """Handle disconnect button click."""
        self.drone_client.disconnect()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self._disable_control_buttons()
        self.console.append_message("Disconnected from drone", "info")

    def _on_arm_clicked(self):
        """Handle arm button click."""
        self.console.append_message("Arming drone...", "info")
        if self.drone_client.arm():
            self.console.append_message("Arming drone successful", "success")
            self.console.append_message("Drone armed", "success")
            self.takeoff_btn.setEnabled(True)
            self.start_mission_btn.setEnabled(True)
        else:
            print("Failed to arm drone")
            self.console.append_message("Failed to arm drone", "error")

    def _on_safety_clicked(self, state):
        """Handle disarm button click."""
        self.console.append_message(f"Safety switch state: {state}")
        self.drone_client.master_connection.safety_switch(state)
        self.safety_btn.setChecked(state)
        self.console.append_message(
            "Drone safety switch " + ("disabled" if state else "enabled"), "success"
        )

    def _on_disarm_clicked(self):
        """Handle disarm button click."""
        if self.drone_client.disarm():
            self.console.append_message("Drone disarmed", "success")
            self.takeoff_btn.setEnabled(False)
            self.start_mission_btn.setEnabled(False)
        else:
            self._show_error("Failed to disarm drone")
            self.console.append_message("Failed to disarm drone", "error")

    def _on_takeoff_clicked(self):
        """Handle takeoff button click."""
        altitude = self.takeoff_alt_input.value()
        if self.drone_client.takeoff(altitude):
            self.console.append_message(f"Taking off to {altitude}m", "success")
            self.takeoff_btn.setEnabled(False)
            self.land_btn.setEnabled(True)
            self.rtl_btn.setEnabled(True)
            self.goto_btn.setEnabled(True)
        else:
            self.console.append_message("Failed to takeoff", "error")

    def _on_land_clicked(self):
        """Handle land button click."""
        if self.drone_client.land():
            self.console.append_message("Landing drone", "success")
            self.land_btn.setEnabled(False)
            self.rtl_btn.setEnabled(False)
            self.goto_btn.setEnabled(False)
            self.takeoff_btn.setEnabled(True)
        else:
            self.console.append_message("Failed to land drone", "error")

    def _on_rtl_clicked(self):
        """Handle return to home button click."""
        if self.drone_client.return_to_home():
            self.console.append_message("Returning to home", "success")
        else:
            self.console.append_message("Failed to return to home", "error")

    def _on_open_map_clicked(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_goto_clicked(self):
        """Handle go to position button click."""
        lat = self.goto_lat_input.value()
        lon = self.goto_lon_input.value()
        alt = self.goto_alt_input.value()

        if self.drone_client.goto_coordinates(lat, lon, alt):
            self.console.append_message(
                f"Moving to position: Lat {lat}, Lon {lon}, Alt {alt}m", "success"
            )
        else:
            self.console.append_message("Failed to move to position", "error")

    def _on_add_waypoint_clicked(self):
        """Handle add waypoint button click."""
        lat = self.waypoint_lat_input.value()
        lon = self.waypoint_lon_input.value()
        alt = self.waypoint_alt_input.value()

        # Add waypoint to the table
        index = self.waypoint_table.rowCount() + 1
        self.waypoint_table.add_waypoint(index, lat, lon, alt)
        self.console.append_message(
            f"Added waypoint {index}: Lat {lat}, Lon {lon}, Alt {alt}m", "info"
        )

    def _on_clear_mission_clicked(self):
        """Handle clear mission button click."""
        self.waypoint_table.clear_waypoints()
        self.console.append_message("Mission cleared", "info")

    def _on_load_mission_clicked(self):
        """Handle load mission button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Mission", "", "Mission Files (*.mission);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                mission_data = json.load(file)

            self.waypoint_table.clear_waypoints()

            for i, waypoint in enumerate(mission_data.get("waypoints", [])):
                self.waypoint_table.add_waypoint(
                    i + 1,
                    waypoint.get("lat", 0),
                    waypoint.get("lon", 0),
                    waypoint.get("alt", 0),
                    waypoint.get("hold", 10),
                )

            self.console.append_message(f"Loaded mission from {file_path}", "success")
        except Exception as e:  # pylint: disable=broad-except
            self._show_error(f"Failed to load mission: {str(e)}")
            self.console.append_message(f"Failed to load mission: {str(e)}", "error")

    def map_event(self, event):
        if event == "move_marker":
            self.dock_content.page().runJavaScript("map.off('click', drawRectangle);")
            self.dock_content.page().runJavaScript(
                "map.off('click', putWaypointEvent);"
            )
            self.dock_content.page().runJavaScript(
                "map.on('click', moveMarkerByClick);"
            )
        elif event == "select_area":
            self.dock_content.page().runJavaScript(
                "map.off('click', putWaypointEvent);"
            )
            self.dock_content.page().runJavaScript(
                "map.off('click', moveMarkerByClick);"
            )
            self.dock_content.page().runJavaScript("map.on('click', drawRectangle);")
        elif event == "set_waypoint":
            self.dock_content.page().runJavaScript(
                "map.off('click', moveMarkerByClick);"
            )
            self.dock_content.page().runJavaScript("map.off('click', drawRectangle);")
            self.dock_content.page().runJavaScript("map.on('click', putWaypointEvent);")
        elif event == "clear_all":
            self.waypoint_table.clear_waypoints()
            self.dock_content.page().runJavaScript("clearAll();")
        # elif event == "undo_waypoint":
        #     self.dock_content.page().runJavaScript("undoWaypoint();")
        # elif event == "choose_field":
        #     self.dock_content.page().runJavaScript("chooseField();")
        elif event == "sync":
            self.dock_content.page().runJavaScript("setMission('ddd');")
            self.dock_content.page().runJavaScript("setPosition();")

    def _create_tab_icon(self, svg_path, size=32):
        renderer = QSvgRenderer(svg_path)

        # Create a pixmap to draw on
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        # Paint the SVG onto the pixmap
        painter = QPainter(pixmap)

        # Apply rotation (90 degrees for West tabs)
        transform = QTransform()
        transform.rotate(90)
        painter.setTransform(transform)
        painter.translate(0, -size)  # Adjust position after rotation

        # Set white color for the icon
        painter.setPen(Qt.white)

        # Draw the SVG
        renderer.render(painter)
        painter.end()

        # Create an icon from the pixmap
        return QIcon(pixmap)

    def _on_save_mission_clicked(self):
        """Handle save mission button click."""
        if self.waypoint_table.rowCount() == 0:
            self.console.append_message("No waypoints to save", "warning")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Mission", "", "Mission Files (*.mission);;All Files (*)"
        )

        if not file_path:
            return

        try:
            mission_data = {
                "waypoints": [w.__dict__ for w in self.waypoint_table.get_waypoints()]
            }

            if not file_path.endswith(".mission"):
                file_path += ".mission"

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(mission_data, file, indent=2)

            self.console.append_message(f"Saved mission to {file_path}", "success")
        except Exception as e:  # pylint: disable=broad-except
            self._show_error(f"Failed to save mission: {str(e)}")
            self.console.append_message(f"Failed to save mission: {str(e)}", "error")

    def _on_upload_mission_clicked(self):
        """Handle upload mission button click."""
        if self.waypoint_table.rowCount() == 0:
            self.console.append_message("No waypoints to upload", "warning")
            return

        _waypoints = self.waypoint_table.get_waypoints()
        waypoints = []
        for wp in _waypoints:
            pose = self.drone_client.initial_position
            waypoints.append(
                Waypoint(
                    lat=float(pose["lat"]),
                    lon=float(pose["lon"]),
                    alt=float(pose["alt"]),
                    hold=10,
                )
            )
            waypoints.append(wp)

        waypoints.append(
            Waypoint(
                lat=float(pose["lat"]),
                lon=float(pose["lon"]),
                alt=float(pose["alt"]),
                hold=10,
            )
        )

        if self.drone_client.upload_mission(waypoints):
            self.console.append_message(
                f"Uploaded mission with {len(waypoints)} waypoints", "success"
            )
            self.start_mission_btn.setEnabled(True)
        else:
            self.console.append_message("Failed to upload mission", "error")

    def _on_start_mission_clicked(self):
        """Handle start mission button click."""
        if self.drone_client.start_mission():
            self.console.append_message("Mission started", "success")
            self.start_mission_btn.setEnabled(False)
            self.cancel_mission_btn.setEnabled(True)
        else:
            self.console.append_message("Failed to start mission", "error")

    def _on_cancel_mission_clicked(self):
        """Handle cancel mission button click."""
        if self.drone_client.cancel_mission():
            self.console.append_message("Mission cancelled", "success")
            self.start_mission_btn.setEnabled(True)
            self.cancel_mission_btn.setEnabled(False)
        else:
            self.console.append_message("Failed to cancel mission", "error")

    def _on_connection_status_changed(self, connected, _):
        """Handle connection status changes."""
        if connected:
            self.connection_status_label.setText("Connected")
            self.arm_btn.setEnabled(True)
        else:
            self.connection_status_label.setText("Disconnected")
            self.arm_btn.setEnabled(False)
            self._disable_control_buttons()

    def _on_drone_status_update(self, status):
        """Handle drone status updates."""
        # Update armed status
        mode_status = status.get("mode", "Unknown")
        self.mode_label.setText(f"{mode_status}")

        is_armemd = status.get("armed", False)
        self.armed_status_label.setText("Armed" if is_armemd else "Disarmed")
        self.safety_btn.setEnabled(self.drone_client.connected)
        self.arm_btn.setEnabled(not is_armemd)
        self.disarm_btn.setEnabled(is_armemd)
        self.takeoff_btn.setEnabled(is_armemd)
        self.goto_btn.setEnabled(is_armemd)

        # Update flight status
        is_flying = status.get("flying", False)
        self.land_btn.setEnabled(is_armemd and is_flying)
        self.rtl_btn.setEnabled(is_armemd and is_flying)
        self.flight_status_label.setText("Flying" if is_flying else "Not Flying")

        # Update position
        position = status.get("position", {})
        if position:
            lat = position.get("lat", 0)
            lon = position.get("lon", 0)
            alt = position.get("alt", 0)

            self.position_label.setText(f"({lat:.7f},{lon:.7f})")
            self.altitude_label.setText(f"{alt:.1f}m")
            self.altitude_gauge.set_value(alt)

            pose = self.drone_client.initial_position
            # print(f"Updating home marker to new position: {lat}, {lon}")
            # print(f"Old home marker position: {pose['lat']}, {pose['lon']}")
            # print(f"Difference: {abs(pose['lat'] - lat)}, {abs(pose['lon'] - lon)}")
            if (
                lat is not None
                and lon is not None
                and pose["lat"] != 0
                and pose["lon"] != 0
                and abs(pose["lat"] - lat) > 1e-6
                and abs(pose["lon"] - lon) > 1e-6
            ):
                self.dock_content.set_drone_marker(lat, lon)

        # orientation
        orientation = status.get("orientation", None)
        if orientation is not None:
            roll = orientation.get("roll", 0)
            pitch = orientation.get("pitch", 0)
            yaw = orientation.get("yaw", 0)
            self.orientation_label.setText(f"R:{roll:.1f}° P:{pitch:.1f}° Y:{yaw:.1f}°")
            self.attitude_indicator.set_attitude(pitch, roll, yaw)
            self.compass_widget.set_heading(yaw)

        self.battery_gauge.set_value(status.get("battery", 100))
        self.battery_progress.setValue(status.get("battery", 100))
        self.speed_gauge.set_value(status.get("speed", 0))

        if status.get("mission_active", False):
            current_wp = status.get("current_waypoint", -1)
            total_wp = status.get("total_waypoints", 0)

            if current_wp > 0 and total_wp > 0:
                progress = int(current_wp * 100 / total_wp)
                self.mission_progress_bar.setValue(progress)
                self.mission_status_label.setText(f"Waypoint {current_wp}/{total_wp}")

    def _on_mission_progress(self, progress, message):
        """Handle mission progress updates."""
        self.mission_progress_bar.setValue(progress)
        self.mission_status_label.setText(message)

    def _disable_control_buttons(self):
        """Disable all control buttons."""
        self.arm_btn.setEnabled(False)
        self.disarm_btn.setEnabled(False)
        self.takeoff_btn.setEnabled(False)
        self.land_btn.setEnabled(False)
        self.rtl_btn.setEnabled(False)
        self.goto_btn.setEnabled(False)
        self.upload_mission_btn.setEnabled(False)
        self.start_mission_btn.setEnabled(False)
        self.cancel_mission_btn.setEnabled(False)

    def _show_error(self, message):
        """Show an error message dialog."""
        QMessageBox.critical(self, "Error", message)

    def eventFilter(self, obj, event):
        # Check for window state change events
        if obj == self:
            is_maximized = self.isMaximized()
            self.dock.setVisible(is_maximized)
            self.map_btn_group.setVisible(is_maximized)

            if not is_maximized:
                self.setGeometry(100, 100, 500, 500)

        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.drone_client.connected:
            msg = MessageBox(
                "Confirm Exit",
                "The drone is still connected. Are you sure you want to exit?",
                self,
            )
            if not msg.exec():
                event.ignore()
                return

        self.dock.setVisible(False)
        time.sleep(0.1)  # Allow time for dock to hide
        if self.drone_client.connected:
            self.drone_client.disconnect()
        event.accept()


def set_theme(app):
    palette = QPalette()

    # Window background (slate gray)
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)

    # Text entry backgrounds (dark gray)
    palette.setColor(QPalette.Base, QColor(42, 42, 42))
    palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    palette.setColor(QPalette.Text, Qt.white)

    # Buttons
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, Qt.white)

    # Hyperlinks
    palette.setColor(QPalette.Link, QColor(42, 130, 218))  # Nice blue

    # Highlights
    palette.setColor(QPalette.Highlight, QColor(90, 140, 200))  # Muted blue
    palette.setColor(QPalette.HighlightedText, Qt.white)

    # Disabled states
    disabled_color = QColor(120, 120, 120)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_color)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_color)

    app.setPalette(palette)


def _set_dark_theme(app):
    palette = QPalette()

    # General window background
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, Qt.white)

    # Text entry background
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.Text, Qt.white)

    # Buttons
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, Qt.white)

    # Hyperlinks
    palette.setColor(QPalette.Link, QColor(0, 122, 204))

    # Selection colors
    palette.setColor(QPalette.Highlight, QColor(38, 79, 120))  # Soft blue
    palette.setColor(QPalette.HighlightedText, Qt.white)

    # Disabled state
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))

    app.setPalette(palette)


def main():
    """Run the drone control application."""
    app = QApplication(sys.argv)

    from src.new_control_station.src.login.page import LoginWindow

    app.setStyle("Fusion")
    set_theme(app)
    # Apply the palette

    window = DroneControlApp()
    window.show()
    # w = LoginWindow(mainWindow=window)
    # w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
