import sys
import json

from PySide6.QtWidgets import (
	QApplication,
	QMainWindow,
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QPushButton,
	QLabel,
	QLineEdit,
	QGroupBox,
	QGridLayout,
	QTableWidget,
	QTableWidgetItem,
	QHeaderView,
	QSpinBox,
	QDoubleSpinBox,
	QMessageBox,
	QTabWidget,
	QTextEdit,
	QProgressBar,
	QFileDialog,
	QMenu,
	QSplitter,
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QFont, QIcon, QColor, QPalette

from pymavlink import mavutil
from controls.mavlink import gz
from controls.mavlink.mission_types import Waypoint


class DroneClient(QObject):
	"""
	Mock drone client that will be replaced with actual implementation.
	"""

	drone_status_update = Signal(dict)
	connection_status = Signal(bool, str)
	mission_progress = Signal(int, str)

	def __init__(self, logger=None):
		super().__init__()
		self.connected = False
		self.tcp_address = ""
		self.tcp_port = 0
		self.k_connected = False
		self.k_tcp_address = ""
		self.k_tcp_port = 0
		self.armed = False
		self.flying = False
		self.current_position = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
		self.k_current_position = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
		self.mission_active = False
		self.mission_waypoints = []
		self.current_waypoint_index = -1
		self.battery = 100
		self.master_connection = None
		self.kamikaze_connection = None
		self.log = logger

		# Setup status update timer
		self.status_timer = QTimer(self)
		self.status_timer.timeout.connect(self._update_status)
		self.status_timer.setInterval(5000)  # Update every second

	def connect_to_drone(self, connection_string, is_kamikaze=False):
		"""Connect to drone at the specified TCP address and port."""

		# In a real implementation, establish TCP connection here

		# if connection is None:
		#     print(f"[MOCK] Failed to connect to drone at {address}:{port}")
		#     self.connection_status.emit(False, "Connection failed")
		#     return False

		if connection_string.startswith("udp:") or connection_string.startswith("tcp:"):
			address, port = connection_string[4:].split(":")
			port = int(port)

		if is_kamikaze:
			self.kamikaze_connection = gz.ArdupilotConnection(connection_string)
			self.k_tcp_address = address
			self.k_tcp_port = port
			self.k_connected = True
			self.kamikaze_connection.wait_heartbeat()
		else:
			self.master_connection = gz.GazeboConnection(
				connection_string=connection_string,
				world="delivery_runway",
				model_name="iris_with_stationary_gimbal",
				camera_link="tilt_link",
				logger=lambda *message: self.log(
					f"[MAVLink] {' '.join(map(str, message))}",
				),
			)
			self.tcp_address = address
			self.tcp_port = port
			self.connected = True

		# Start status updates
		self.status_timer.start()

		self.connection_status.emit(
			True,
			f"[MAVLink] Connected to {address}:{port} for {'Kamikaze' if is_kamikaze else 'Drone'}",
		)
		# self.connection_status.emit(True, f"[MAVLink] Heartbeat from system {connection.target_system}, component {connection.target_component}")
		return True

	def set_logger(self, logger):
		self.log = logger

	def disconnect(self, is_kamikaze=False):
		"""Disconnect from the drone."""
		if self.connected:
			self.status_timer.stop()
			if is_kamikaze:
				self.kamikaze_connection.close()
			else:
				self.master_connection.close()

			self.connected = False
			self.armed = False
			self.flying = False
			self.mission_active = False
			self.status_timer.stop()
			self.connection_status.emit(
				False,
				f"[MAVLink] Disconnecting from drone at {self.tcp_address}:{self.tcp_port}",
			)

	def arm(self, is_kamikaze=False):
		"""Arm the drone. and enable streaming."""
		if not self.connected:
			return False
		print("Arming drone...")

		if is_kamikaze:
			self.kamikaze_connection.arm()
		else:
			self.master_connection.arm()
		done = self.master_connection.enable_streaming()
		if not done:
			print("❌ Failed to enable streaming.")
			return False
		self.armed = True

		if is_kamikaze:
			location = self.kamikaze_connection.get_current_gps_location()
		else:
			location = self.master_connection.get_current_gps_location()

		if location is None:
			print("❌ Failed to get current GPS location.")
			exit(1)

		lat, lon, alt = location
		if is_kamikaze:
			self.k_current_position = {"lat": lat, "lon": lon, "alt": alt}
		else:
			self.current_position = {"lat": lat, "lon": lon, "alt": alt}
		return True

	def disarm(self):
		"""Disarm the drone."""
		if not self.connected:
			return False

		if not self.armed or not self.flying:
			self.log("Disarming a unarmed or not flying drone")

		self.armed = False
		self.master_connection.disarm()
		return True

	def takeoff(self, altitude):
		"""Take off to the specified altitude."""
		if not self.connected or not self.armed or self.flying:
			return False

		self.master_connection.takeoff(altitude)
		self.flying = True
		self.current_position["alt"] = altitude
		return True

	def land(self):
		"""Land the drone."""
		if not self.connected or not self.flying:
			return False

		print("[MOCK] Landing drone")
		self.flying = False
		self.current_position["alt"] = 0.0
		return True

	def return_to_home(self):
		"""Return to launch location."""
		if not self.connected or not self.flying:
			return False

		self.master_connection.return_to_launch()
		# In a real implementation, send RTL command
		self.mission_active = False
		return True

	def goto_coordinates(self, lat, lon, alt):
		"""Move to the specified coordinates."""
		if not self.connected or not self.flying:
			return False
		curr_lat = self.current_position["lat"]
		curr_lon = self.current_position["lon"]

		self.master_connection.goto_waypointv2(curr_lat + lat, curr_lon + lon, alt)

		print(f"[MOCK] Moving to coordinates: Lat {lat}, Lon {lon}, Alt {alt}m")
		self.current_position = {"lat": lat, "lon": lon, "alt": alt}
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
		if not self.connected or not self.armed or not self.mission_waypoints:
			return False

		print("[MOCK] Starting mission")
		self.mission_active = True
		self.flying = True
		self.current_waypoint_index = 0
		self.mission_completed = False

		self.master_connection.start_mission()
		self.mission_progress.emit(0, "Mission started")

		def _update_status_hook(current, done):
			self.current_waypoint_index = current
			self.mission_completed = done
			msg = f"Moving to waypoint {current + 1}/{len(self.mission_waypoints)}"
			self.mission_progress.emit(
				int((current + 1) * 100 / len(self.mission_waypoints)), msg
			)

		self.master_connection.monitor_mission_progress(
			timeout=10000,
			_update_status_hook=_update_status_hook,
		)

		# Simulate mission execution
		# for i, waypoint in enumerate(self.mission_waypoints):
		# 	self.current_waypoint_index = i
		# 	self.mission_progress.emit(
		# 		int((i + 1) * 100 / len(self.mission_waypoints)), msg
		# 	)
		# 	# In real implementation, this would be asynchronous
		# 	self.current_position = {
		# 		"lat": waypoint.lat,
		# 		"lon": waypoint.lon,
		# 		"alt": waypoint.alt,
		# 	}

		return True

	def clear_mission(self):
		self.master_connection.clear_mission()
		return

	def cancel_mission(self):
		"""Cancel the current mission."""
		if not self.connected or not self.mission_active:
			return False

		print("[MOCK] Cancelling mission")
		self.mission_active = False
		self.current_waypoint_index = -1
		self.mission_progress.emit(0, "Mission cancelled")
		return True

	def _update_status(self):
		"""Update and emit drone status information."""
		# Simulate battery drain
		if self.flying and self.battery > 10:
			self.battery -= 1
		status = self.master_connection.get_status()
		# status = {
		#     "connected": self.connected,
		#     "armed": self.armed,
		#     "flying": self.flying,
		#     "position": self.current_position,
		#     "mission_active": self.mission_active,
		#     "current_waypoint": self.current_waypoint_index,
		#     "total_waypoints": len(self.mission_waypoints),
		#     "battery": self.battery
		# }

		self.drone_status_update.emit(status)


class MissionWaypointTable(QTableWidget):
	"""
	Table widget for displaying and editing mission waypoints.
	"""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setColumnCount(5)
		self.setHorizontalHeaderLabels(
			["#", "Latitude", "Longitude", "Altitude (m)", "Hold", "Actions"]
		)
		self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.setEditTriggers(QTableWidget.DoubleClicked)
		self.verticalHeader().setVisible(False)

	def add_waypoint(self, index, lat, lon, alt, hold=10):
		"""Add a new waypoint to the table."""
		row = self.rowCount()
		self.insertRow(row)

		# Add waypoint data
		self.setItem(row, 0, QTableWidgetItem(str(index)))
		self.setItem(row, 1, QTableWidgetItem(str(lat)))
		self.setItem(row, 2, QTableWidgetItem(str(lon)))
		self.setItem(row, 3, QTableWidgetItem(str(alt)))
		self.setItem(row, 4, QTableWidgetItem(str(hold)))

		# Add delete button
		delete_btn = QPushButton("Delete")
		delete_btn.clicked.connect(
			lambda: self.removeRow(self.indexAt(delete_btn.pos()).row())
		)
		self.setCellWidget(row, 5, delete_btn)

	def clear_waypoints(self):
		"""Clear all waypoints from the table."""
		self.setRowCount(0)

	def get_waypoints(self):
		"""Get all waypoints from the table."""
		waypoints = []
		for row in range(self.rowCount()):
			waypoint = Waypoint(
				lat=float(self.item(row, 1).text()),
				lon=float(self.item(row, 2).text()),
				alt=float(self.item(row, 3).text()),
				hold=int(self.item(row, 4).text()),
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
		self.drone_client.connection_status.connect(self._on_connection_status_changed)
		self.drone_client.drone_status_update.connect(self._on_drone_status_update)
		self.drone_client.mission_progress.connect(self._on_mission_progress)

		# Initialize UI components
		self._init_ui()

		# Set window properties
		self.setWindowTitle("MATEK Drone Control Center")
		self.resize(900, 700)

		# Log application start
		self.console.append_message("Drone Control Center started", "info")
		self.drone_client.set_logger(self.console.append_message)

	def _init_ui(self):
		"""Initialize the UI components."""
		# Create main widget and layout
		main_widget = QWidget()
		main_layout = QVBoxLayout(main_widget)

		# Create connection controls
		connection_group = QGroupBox("Connection")
		connection_layout = QVBoxLayout(connection_group)
		main_connection_group = QGroupBox("")
		main_connection_layout = QHBoxLayout(main_connection_group)
		kamikaze_connection_group = QGroupBox("")
		kamikaze_connection_layout = QHBoxLayout(kamikaze_connection_group)

		self.tcp_address_input = QLineEdit("127.0.0.1")
		self.tcp_port_input = QSpinBox()
		self.tcp_port_input.setRange(1, 65535)
		self.tcp_port_input.setValue(14550)

		self.connect_btn = QPushButton("Connect")
		self.connect_btn.clicked.connect(self._on_connect_clicked)
		self.connect_menu = QMenu(self)
		self.connect_action = self.connect_menu.addAction("Standard Connect")
		self.connect_action.triggered.connect(lambda: self._on_connect_clicked)
		self.connect_action = self.connect_menu.addAction("TCP Connect")
		self.connect_action.triggered.connect(
			lambda: self._on_connect_clicked(_type="tcp")
		)
		self.connect_auto_action = self.connect_menu.addAction("Serial (/dev/ttyAMA0)")
		self.connect_auto_action.triggered.connect(self._on_serial_connect_clicked)
		self.connect_sitl_action = self.connect_menu.addAction("USB (/dev/ttyUSB0)")
		self.connect_sitl_action.triggered.connect(self._on_usb_connect_clicked)
		self.connect_btn.setMenu(self.connect_menu)

		self.disconnect_btn = QPushButton("Disconnect")
		self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
		self.disconnect_btn.setEnabled(False)

		self.k_tcp_address_input = QLineEdit("127.0.0.1")
		self.k_tcp_port_input = QSpinBox()
		self.k_tcp_port_input.setRange(1, 65535)
		self.k_tcp_port_input.setValue(14560)

		self.k_connect_btn = QPushButton("Connect")
		self.k_connect_btn.clicked.connect(self._on_connect_clicked)

		self.k_disconnect_btn = QPushButton("Disconnect")
		self.k_disconnect_btn.clicked.connect(self._on_disconnect_clicked)
		self.k_disconnect_btn.setEnabled(False)

		connection_layout.addWidget(main_connection_group)
		connection_layout.addWidget(kamikaze_connection_group)

		main_connection_layout.addWidget(QLabel("Drone Address:"))
		main_connection_layout.addWidget(self.tcp_address_input)
		main_connection_layout.addWidget(QLabel("Port:"))
		main_connection_layout.addWidget(self.tcp_port_input)
		main_connection_layout.addWidget(self.connect_btn)
		main_connection_layout.addWidget(self.disconnect_btn)

		kamikaze_connection_layout.addWidget(QLabel("Kamikaze Address:"))
		kamikaze_connection_layout.addWidget(self.k_tcp_address_input)
		kamikaze_connection_layout.addWidget(QLabel("Port:"))
		kamikaze_connection_layout.addWidget(self.k_tcp_port_input)
		kamikaze_connection_layout.addWidget(self.k_connect_btn)
		kamikaze_connection_layout.addWidget(self.k_disconnect_btn)

		# Create tab widget for different control panels
		tab_widget = QTabWidget()

		# Basic controls tab
		basic_control_widget = QWidget()
		basic_control_layout = QVBoxLayout(basic_control_widget)

		# Create drone control buttons
		control_group = QGroupBox("Drone Controls")
		control_layout = QVBoxLayout(control_group)

		# First row of controls
		controls_row1 = QHBoxLayout()

		self.arm_btn = QPushButton("Arm")
		self.arm_btn.clicked.connect(self._on_arm_clicked)
		self.arm_btn.setEnabled(False)

		self.disarm_btn = QPushButton("Disarm")
		self.disarm_btn.clicked.connect(self._on_disarm_clicked)
		self.disarm_btn.setEnabled(False)

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
		self.goto_alt_input.setValue(10.0)

		self.goto_btn = QPushButton("Go")
		self.goto_btn.clicked.connect(self._on_goto_clicked)
		self.goto_btn.setEnabled(False)

		goto_layout.addWidget(QLabel("Latitude:"))
		goto_layout.addWidget(self.goto_lat_input)
		goto_layout.addWidget(QLabel("Longitude:"))
		goto_layout.addWidget(self.goto_lon_input)
		goto_layout.addWidget(QLabel("Altitude (m):"))
		goto_layout.addWidget(self.goto_alt_input)
		goto_layout.addWidget(self.goto_btn)

		# Add takeoff altitude spinner
		takeoff_layout = QHBoxLayout()
		takeoff_layout.addWidget(QLabel("Takeoff Altitude (m):"))
		self.takeoff_alt_input = QDoubleSpinBox()
		self.takeoff_alt_input.setRange(1, 100)
		self.takeoff_alt_input.setValue(5.0)
		takeoff_layout.addWidget(self.takeoff_alt_input)
		takeoff_layout.addStretch()

		# Add all controls to the layout
		control_layout.addLayout(controls_row1)
		control_layout.addLayout(takeoff_layout)
		basic_control_layout.addWidget(control_group)
		basic_control_layout.addWidget(goto_group)

		# Create status display
		status_group = QGroupBox("Drone Status")
		status_layout = QGridLayout(status_group)

		self.connection_status_label = QLabel("Not Connected")
		self.armed_status_label = QLabel("Disarmed")
		self.flight_status_label = QLabel("Not Flying")
		self.position_label = QLabel("Position: N/A")
		self.altitude_label = QLabel("Altitude: N/A")
		self.battery_label = QLabel("Battery: N/A")
		self.battery_progress = QProgressBar()
		self.battery_progress.setRange(0, 100)

		# Add status widgets to grid
		status_layout.addWidget(QLabel("Connection:"), 0, 0)
		status_layout.addWidget(self.connection_status_label, 0, 1)
		status_layout.addWidget(QLabel("Armed:"), 0, 2)
		status_layout.addWidget(self.armed_status_label, 0, 3)
		status_layout.addWidget(QLabel("Flight:"), 1, 0)
		status_layout.addWidget(self.flight_status_label, 1, 1)
		status_layout.addWidget(QLabel("Position:"), 1, 2)
		status_layout.addWidget(self.position_label, 1, 3)
		status_layout.addWidget(QLabel("Battery:"), 2, 0)
		status_layout.addWidget(self.battery_label, 2, 1)
		status_layout.addWidget(self.battery_progress, 2, 2, 1, 2)

		# Add status group to basic control layout
		basic_control_layout.addWidget(status_group)
		basic_control_layout.addStretch(1)

		# Mission planning tab
		mission_widget = QWidget()
		mission_layout = QVBoxLayout(mission_widget)

		# Mission waypoints table
		mission_layout.addWidget(QLabel("Mission Waypoints:"))
		self.waypoint_table = MissionWaypointTable()
		mission_layout.addWidget(self.waypoint_table)

		# Mission controls
		mission_controls_layout = QHBoxLayout()

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

		# Console output tab
		console_widget = QWidget()
		console_layout = QVBoxLayout(console_widget)

		console_layout.addWidget(QLabel("Console Output:"))
		self.console = ConsoleOutput()
		console_layout.addWidget(self.console)

		# Add tabs to the tab widget
		tab_widget.addTab(basic_control_widget, "Basic Controls")
		tab_widget.addTab(mission_widget, "Mission Planning")
		tab_widget.addTab(console_widget, "Console")

		# Add widgets to main layout
		main_layout.addWidget(connection_group)
		main_layout.addWidget(tab_widget)

		# Set central widget
		self.setCentralWidget(main_widget)

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

		self.console.append_message(f"Connecting to {address}:{port}...", "info")
		connection_string = f"{_type}:{address}:{port}"
		if self.drone_client.connect_to_drone(connection_string):
			self.connect_btn.setEnabled(False)
			self.disconnect_btn.setEnabled(True)
			self.arm_btn.setEnabled(True)
			self.upload_mission_btn.setEnabled(True)
			self.console.append_message(f"Connected to {address}:{port}", "success")
		else:
			self.console.append_message(
				f"Failed to connect to {address}:{port}", "error"
			)

	def _on_serial_connect_clicked(self):
		"""Handle connect button click."""

		serial_connection_string = "/dev/ttyAMA0"
		self.console.append_message(
			f"Connecting to {serial_connection_string}...", "info"
		)
		if self.drone_client.connect_to_drone(serial_connection_string):
			self.connect_btn.setEnabled(False)
			self.disconnect_btn.setEnabled(True)
			self.arm_btn.setEnabled(True)
			self.upload_mission_btn.setEnabled(True)
			self.console.append_message(
				f"Connected to {serial_connection_string}", "success"
			)
		else:
			self.console.append_message(
				f"Failed to connect to {serial_connection_string}", "error"
			)

	def _on_usb_connect_clicked(self):
		"""Handle connect button click."""
		usb_connection_string = "/dev/ttyUSB0"
		self.console.append_message(f"Connecting to {usb_connection_string}...", "info")

		if self.drone_client.connect_to_drone(usb_connection_string):
			self.connect_btn.setEnabled(False)
			self.disconnect_btn.setEnabled(True)
			self.arm_btn.setEnabled(True)
			self.upload_mission_btn.setEnabled(True)
			self.console.append_message(
				f"Connected to {usb_connection_string}", "success"
			)
		else:
			self.console.append_message(
				f"Failed to connect to {usb_connection_string}", "error"
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
		if self.drone_client.arm():
			self.console.append_message("Drone armed", "success")
			self.arm_btn.setEnabled(False)
			self.disarm_btn.setEnabled(True)
			self.takeoff_btn.setEnabled(True)
			self.start_mission_btn.setEnabled(True)
		else:
			self.console.append_message("Failed to arm drone", "error")

	def _on_disarm_clicked(self):
		"""Handle disarm button click."""
		if self.drone_client.disarm():
			self.console.append_message("Drone disarmed", "success")
			self.arm_btn.setEnabled(True)
			self.disarm_btn.setEnabled(False)
			self.takeoff_btn.setEnabled(False)
			self.start_mission_btn.setEnabled(False)
		else:
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
			with open(file_path, "r") as file:
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
		except Exception as e:
			self.console.append_message(f"Failed to load mission: {str(e)}", "error")

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
			mission_data = {"waypoints": self.waypoint_table.get_waypoints()}

			if not file_path.endswith(".mission"):
				file_path += ".mission"

			with open(file_path, "w") as file:
				json.dump(mission_data, file, indent=2)

			self.console.append_message(f"Saved mission to {file_path}", "success")
		except Exception as e:
			self.console.append_message(f"Failed to save mission: {str(e)}", "error")

	def _on_upload_mission_clicked(self):
		"""Handle upload mission button click."""
		if self.waypoint_table.rowCount() == 0:
			self.console.append_message("No waypoints to upload", "warning")
			return

		waypoints = self.waypoint_table.get_waypoints()

		if self.drone_client.upload_mission(waypoints):
			self.console.append_message(
				f"Uploaded mission with {len(waypoints)} waypoints", "success"
			)
			self.start_mission_btn.setEnabled(self.drone_client.armed)
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

	def _on_connection_status_changed(self, connected, message):
		"""Handle connection status changes."""
		if connected:
			self.connection_status_label.setText("Connected")
		else:
			self.connection_status_label.setText("Disconnected")
			self._disable_control_buttons()

	def _on_drone_status_update(self, status):
		"""Handle drone status updates."""
		# Update armed status
		if status.get("armed", False):
			self.armed_status_label.setText("Armed")
			self.arm_btn.setEnabled(False)
			self.disarm_btn.setEnabled(True)
		else:
			self.arm_btn.setEnabled(True)
			self.disarm_btn.setEnabled(False)
			self.armed_status_label.setText("Disarmed")

		# Update flight status
		if status.get("flying", False):
			self.flight_status_label.setText("Flying")
		else:
			self.flight_status_label.setText("Not Flying")

		# Update position
		position = status.get("position", {})
		if position:
			lat = position.get("lat", 0)
			lon = position.get("lon", 0)
			alt = position.get("alt", 0)
			self.position_label.setText(f"Lat: {lat:.7f}, Lon: {lon:.7f}")
			self.altitude_label.setText(f"Alt: {alt:.1f}m")

		# Update battery
		battery = status.get("battery", 0).get("remaining", 0)
		self.battery_label.setText(f"Battery: {battery}%")
		self.battery_progress.setValue(battery)

		# Set battery progress bar color based on level
		if battery <= 20:
			self.battery_progress.setStyleSheet(
				"QProgressBar::chunk { background-color: red; }"
			)
		elif battery <= 50:
			self.battery_progress.setStyleSheet(
				"QProgressBar::chunk { background-color: orange; }"
			)
		else:
			self.battery_progress.setStyleSheet(
				"QProgressBar::chunk { background-color: green; }"
			)

		# Update mission status
		if status.get("mission_active", False):
			current_wp = status.get("current_waypoint", -1) + 1
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

	def closeEvent(self, event):
		"""Handle window close event."""
		if self.drone_client.connected:
			self.drone_client.disconnect()
		event.accept()


def main():
	"""Run the drone control application."""
	app = QApplication(sys.argv)
	window = DroneControlApp()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
