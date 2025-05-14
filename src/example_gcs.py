import sys
import time
import cv2
import json

from PySide6.QtWidgets import (
	QApplication,
	QMainWindow,
	QWidget,
	QStackedWidget,
	QTableWidget,
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
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QImage, QPixmap
from .mq.messages import ZMQTopics
from .mq.example_zmq_reciever import Client as ZMQClient
from pymavlink import mavutil
from .controls.mavlink import gz
from .controls.mavlink.mission_types import Waypoint


class DroneClient(QObject):
	"""
	Mock drone client that will be replaced with actual implementation.
	"""

	drone_status_update = Signal(dict)
	connection_status = Signal(bool, str)
	mission_progress = Signal(int, str)

	def __init__(
		self,
		zmq_client: ZMQClient = None,
		logger=None,
		video_stream_window=None,
		processed_stream_window=None,
		is_simulation=False,
	):
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
		self.zmq_client = zmq_client
		self.video_stream_window = video_stream_window
		self.processed_stream_window = processed_stream_window
		self.is_simulation = is_simulation

		# Setup status update timer
		self.status_timer = QTimer(self)
		self.status_timer.timeout.connect(self._update_status)
		self.status_timer.setInterval(5000)  # Update every second

		# Setup video stream thread
		self.video_running = False
		self.video_timer = QTimer(self)
		self.video_timer.timeout.connect(self._video_stream)
		self.video_timer.setInterval(100)  # Update every 100ms

	def drop_load(self):
		"""Drop load command."""
		if not self.connected:
			return False

		msg = self.zmq_client.send_command(ZMQTopics.DROP_LOAD)
		self.log(msg)
		return

	def pick_load(self):
		"""Pick load command."""
		if not self.connected:
			return False

		msg = self.zmq_client.send_command(ZMQTopics.PICK_LOAD)
		self.log(msg)
		return

	def raise_hook(self):
		"""Raise hook command."""
		if not self.connected:
			return False

		msg = self.zmq_client.send_command(ZMQTopics.RAISE_HOOK)
		self.log(msg)
		return

	def drop_hook(self):
		"""Drop hook command."""
		if not self.connected:
			return False

		msg = self.zmq_client.send_command(ZMQTopics.DROP_HOOK)
		self.log(msg)
		return

	def connect_to_drone(self, connection_string, is_kamikaze=False):
		"""Connect to drone at the specified TCP address and port."""

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
		print("Starting status timer")
		self.video_timer.start()

		self.video_stream_window.show()
		self.processed_stream_window.show()

		self.processed_stream_window.start()
		self.video_stream_window.start()

		# set windows frame dimensions
		frame = self.zmq_client.get_current_frame()
		if frame is not None:
			sh = frame.shape
			self.video_stream_window.setWindowSize(sh[1], sh[0])
			self.processed_stream_window.setWindowSize(sh[1], sh[0])

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
			if is_kamikaze:
				self.kamikaze_connection.close()
			else:
				self.master_connection.close()

			self.connected = False
			self.armed = False
			self.flying = False
			self.mission_active = False

			self.status_timer.stop()
			self.video_timer.stop()

			self.video_stream_window.close()
			self.processed_stream_window.close()

			self.connection_status.emit(
				False,
				f"[MAVLink] Disconnecting from drone at {self.tcp_address}:{self.tcp_port}",
			)

	def arm(self, is_kamikaze=False):
		"""Arm the drone."""
		if not self.connected:
			return False
		print("Arming drone...")

		if is_kamikaze:
			self.kamikaze_connection.arm()
		else:
			self.master_connection.arm()

		if self.connected and self.is_simulation:
			done = self.master_connection.enable_streaming()
			if not done:
				print("❌ Failed to enable streaming.")
		self.armed = True

		if is_kamikaze:
			location = self.kamikaze_connection.get_current_gps_location()
		else:
			location = self.master_connection.get_current_gps_location()

		if location is None:
			print("❌ Failed to get current GPS location.")
			exit(1)

		self.armed = True
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

		self.master_connection.land()
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

		self.mission_progress_timer = QTimer(self)
		self.mission_progress_timer.timeout.connect(
			lambda: self.master_connection.monitor_mission_progress(
				timeout=10000,
				_update_status_hook=_update_status_hook,
				in_loop=True,
			)
		)
		self.mission_progress_timer.start(1000)

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

	def cancel_mission(self):
		"""Cancel the current mission."""
		if not self.connected or not self.mission_active:
			return False

		self.master_connection.clear_mission()
		self.mission_active = False
		self.current_waypoint_index = -1
		self.mission_progress.emit(0, "Mission cancelled")
		return True

	def _video_stream(self):
		"""Thread function to handle video receiving"""
		# Display loop for video frames and handle keyboard commands
		self.zmq_client.get_video_stream(imshow_func=self.video_stream_window.imshow)
		self.zmq_client.get_processed_stream(
			imshow_func=self.processed_stream_window.imshow
		)

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


class CameraDisplay(QMainWindow):
	def __init__(self, title="Camera Display", scale=0.5, frame_shape=(1280, 720, 3)):
		super().__init__()
		self.setWindowTitle(title)

		self.scale = scale  # Scale factor for display
		self.frame = None

		self.orig_height, self.orig_width, self.channels = frame_shape

		# Calculate display dimensions
		self.disp_width = int(self.orig_width * self.scale)
		self.disp_height = int(self.orig_height * self.scale)

		# Set window size
		self.setGeometry(100, 100, self.disp_width, self.disp_height)

		# Create and position the label that will hold the video
		self.label = QLabel(self)
		self.label.setGeometry(0, 0, self.disp_width, self.disp_height)

	def setWindowSize(self, width, height, channels=3):
		"""Set the window size and position."""
		self.disp_height = int(height * self.scale)
		self.disp_width = int(width * self.scale)
		self.setGeometry(100, 100, self.disp_width, self.disp_height)
		self.channels = channels

		# Update the label geometry to match the new window size
		self.label.setGeometry(0, 0, self.disp_width, self.disp_height)

	def _update_frame(self):
		if self.frame is None:
			return
		# First convert color space
		frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

		# Then resize the frame
		frame = cv2.resize(frame, (self.disp_width, self.disp_height))

		# Calculate bytes per line based on the resized image
		bytes_per_line = self.channels * self.disp_width

		# Create QImage with the resized data
		q_img = QImage(
			frame.data,
			self.disp_width,
			self.disp_height,
			bytes_per_line,
			QImage.Format_RGB888,
		)

		self.label.setPixmap(QPixmap.fromImage(q_img))

	def start(self):
		# Start the timer to update frames
		self.timer = QTimer()
		self.timer.timeout.connect(self._update_frame)
		self.timer.start(100)

	def imshow(self, frame):
		self.frame = frame


class DroneControlApp(QMainWindow):
	"""
	Main application window for drone control.
	"""

	def __init__(
		self, client, video_stream_window, processed_stream_window, is_simulation=False
	):
		super().__init__()

		# Set application properties
		QApplication.instance().setProperty("timestamp_fn", self._get_timestamp)

		# external windows
		self.video_stream_window = video_stream_window
		self.processed_stream_window = processed_stream_window

		# Initialize UI components

		# Initialize drone client
		self.drone_client = DroneClient(
			zmq_client=client,
			video_stream_window=self.video_stream_window,
			processed_stream_window=self.processed_stream_window,
			is_simulation=is_simulation,
		)

		self._init_ui()
		self.drone_client.set_logger(self.console.append_message)

		self.drone_client.connection_status.connect(self._on_connection_status_changed)
		self.drone_client.drone_status_update.connect(self._on_drone_status_update)
		self.drone_client.mission_progress.connect(self._on_mission_progress)

		# Set window properties
		self.setWindowTitle("MATEK Drone Control Center")
		self.resize(900, 700)

		# Log application start
		self.console.append_message("Drone Control Center started", "info")
		self.drone_client.set_logger(self.console.append_message)

	def _init_ui(self):
		"""Initialize the UI components with a modern design."""
		# Set application-wide style
		self.setStyleSheet("""
	        QMainWindow, QWidget { background-color: #111111; color: #FFFFFF; }
	        QGroupBox { 
	            border: 1px solid #333333; 
	            border-radius: 6px; 
	            margin-top: 12px; 
	            font-weight: bold;
	            padding-top: 8px;
	        }
	        QGroupBox::title { 
	            subcontrol-origin: margin; 
	            left: 10px; 
	            padding: 0 5px;
	        }
	        QLabel { color: #CCCCCC; }
	        QTabWidget::pane { 
	            border: 1px solid #333333;
	            border-radius: 6px;
	        }
	        QTabBar::tab {
	            background-color: #222222;
	            color: #AAAAAA;
	            border-top-left-radius: 4px;
	            border-top-right-radius: 4px;
	            padding: 8px 16px;
	            margin-right: 2px;
	        }
	        QTabBar::tab:selected {
	            background-color: #1E88E5;
	            color: white;
	        }
	        QPushButton {
	            background-color: #1E88E5;
	            color: white;
	            border: none;
	            border-radius: 4px;
	            padding: 8px 16px;
	            font-weight: bold;
	        }
	        QPushButton:hover {
	            background-color: #1976D2;
	        }
	        QPushButton:disabled {
	            background-color: #555555;
	            color: #888888;
	        }
	        QLineEdit, QSpinBox, QDoubleSpinBox {
	            background-color: #333333;
	            color: white;
	            border: 1px solid #444444;
	            border-radius: 4px;
	            padding: 6px;
	        }
	        QProgressBar {
	            border: 1px solid #444444;
	            border-radius: 4px;
	            background-color: #333333;
	            text-align: center;
	        }
	        QProgressBar::chunk {
	            background-color: #1E88E5;
	            border-radius: 4px;
	        }
	    """)

		# Create main widget and layout
		main_widget = QWidget()
		main_layout = QVBoxLayout(main_widget)
		main_layout.setContentsMargins(15, 15, 15, 15)
		main_layout.setSpacing(10)

		# Create navigation sidebar and content area
		nav_content_splitter = QSplitter(Qt.Horizontal)

		# Navigation sidebar
		nav_widget = QWidget()
		nav_widget.setMaximumWidth(200)
		nav_layout = QVBoxLayout(nav_widget)
		nav_layout.setContentsMargins(0, 0, 0, 0)

		# App title
		app_title = QLabel("MATEK GCS")
		app_title.setStyleSheet(
			"font-size: 18px; font-weight: bold; color: white; margin-bottom: 20px;"
		)
		app_title.setAlignment(Qt.AlignCenter)
		nav_layout.addWidget(app_title)

		# Navigation buttons
		self.nav_connection_btn = QPushButton("Connection")
		self.nav_connection_btn.setStyleSheet("text-align: left; padding: 10px;")
		self.nav_connection_btn.clicked.connect(
			lambda: self.stacked_widget.setCurrentIndex(0)
		)

		self.nav_basic_control_btn = QPushButton("Basic Control")
		self.nav_basic_control_btn.setStyleSheet("text-align: left; padding: 10px;")
		self.nav_basic_control_btn.clicked.connect(
			lambda: self.stacked_widget.setCurrentIndex(1)
		)

		self.nav_mission_btn = QPushButton("Mission Planning")
		self.nav_mission_btn.setStyleSheet("text-align: left; padding: 10px;")
		self.nav_mission_btn.clicked.connect(
			lambda: self.stacked_widget.setCurrentIndex(2)
		)

		self.nav_console_btn = QPushButton("Console")
		self.nav_console_btn.setStyleSheet("text-align: left; padding: 10px;")
		self.nav_console_btn.clicked.connect(
			lambda: self.stacked_widget.setCurrentIndex(3)
		)

		self.nav_auth_btn = QPushButton("Authentication")
		self.nav_auth_btn.setStyleSheet("text-align: left; padding: 10px;")
		self.nav_auth_btn.clicked.connect(
			lambda: self.stacked_widget.setCurrentIndex(4)
		)

		nav_layout.addWidget(self.nav_connection_btn)
		nav_layout.addWidget(self.nav_basic_control_btn)
		nav_layout.addWidget(self.nav_mission_btn)
		nav_layout.addWidget(self.nav_console_btn)
		nav_layout.addWidget(self.nav_auth_btn)
		nav_layout.addStretch()

		# Status indicators in sidebar
		status_widget = QWidget()
		status_layout = QVBoxLayout(status_widget)
		status_layout.setContentsMargins(5, 5, 5, 5)

		# Connection status indicator
		connection_status_layout = QHBoxLayout()
		connection_indicator = QLabel("•")
		connection_indicator.setStyleSheet("color: #FF5252; font-size: 24px;")
		self.connection_status_label = QLabel("Disconnected")
		connection_status_layout.addWidget(connection_indicator)
		connection_status_layout.addWidget(self.connection_status_label)
		status_layout.addLayout(connection_status_layout)

		# Battery status in sidebar
		battery_layout = QHBoxLayout()
		battery_layout.addWidget(QLabel("Battery:"))
		self.battery_progress = QProgressBar()
		self.battery_progress.setRange(0, 100)
		self.battery_progress.setValue(0)
		battery_layout.addWidget(self.battery_progress)
		status_layout.addLayout(battery_layout)

		nav_layout.addWidget(status_widget)

		# Content area with stacked widget for multiple "pages"
		content_widget = QWidget()
		content_layout = QVBoxLayout(content_widget)
		content_layout.setContentsMargins(0, 0, 0, 0)

		self.stacked_widget = QStackedWidget()

		# 1. Connection Page
		connection_page = QWidget()
		connection_layout = QVBoxLayout(connection_page)
		connection_layout.setSpacing(15)

		# Page title
		connection_title = QLabel("Connection Settings")
		connection_title.setStyleSheet(
			"font-size: 24px; font-weight: bold; margin-bottom: 20px;"
		)
		connection_layout.addWidget(connection_title)

		# Main drone connection panel
		main_connection_group = QGroupBox("Main Drone Connection")
		main_connection_layout = QGridLayout(main_connection_group)
		main_connection_layout.setColumnStretch(1, 1)

		main_connection_layout.addWidget(QLabel("Drone Address:"), 0, 0)
		self.tcp_address_input = QLineEdit("127.0.0.1")
		main_connection_layout.addWidget(self.tcp_address_input, 0, 1)

		main_connection_layout.addWidget(QLabel("Port:"), 0, 2)
		self.tcp_port_input = QSpinBox()
		self.tcp_port_input.setRange(1, 65535)
		self.tcp_port_input.setValue(14550)
		main_connection_layout.addWidget(self.tcp_port_input, 0, 3)

		connection_buttons_layout = QHBoxLayout()

		self.connect_btn = QPushButton("Connect")
		self.connect_btn.setStyleSheet("background-color: #4CAF50;")
		self.connect_btn.clicked.connect(lambda: self._on_connect_clicked())

		self.connect_menu = QMenu(self)
		self.connect_menu.setStyleSheet("background-color: #222222; color: white;")
		self.connect_action = self.connect_menu.addAction("Standard Connect")
		self.connect_action.triggered.connect(lambda: self._on_connect_clicked())
		self.tcp_connect_action = self.connect_menu.addAction("TCP Connect")
		self.tcp_connect_action.triggered.connect(
			lambda: self._on_connect_clicked(_type="tcp")
		)
		self.connect_auto_action = self.connect_menu.addAction("Serial (/dev/ttyAMA0)")
		self.connect_auto_action.triggered.connect(self._on_serial_connect_clicked)
		self.connect_sitl_action = self.connect_menu.addAction("USB (/dev/ttyUSB0)")
		self.connect_sitl_action.triggered.connect(self._on_usb_connect_clicked)
		self.connect_btn.setMenu(self.connect_menu)

		self.disconnect_btn = QPushButton("Disconnect")
		self.disconnect_btn.setStyleSheet("background-color: #F44336;")
		self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
		self.disconnect_btn.setEnabled(False)

		connection_buttons_layout.addWidget(self.connect_btn)
		connection_buttons_layout.addWidget(self.disconnect_btn)

		main_connection_layout.addLayout(connection_buttons_layout, 1, 0, 1, 4)

		# Kamikaze drone connection
		kamikaze_connection_group = QGroupBox("Kamikaze Drone Connection")
		kamikaze_connection_layout = QGridLayout(kamikaze_connection_group)
		kamikaze_connection_layout.setColumnStretch(1, 1)

		kamikaze_connection_layout.addWidget(QLabel("Kamikaze Address:"), 0, 0)
		self.k_tcp_address_input = QLineEdit("127.0.0.1")
		kamikaze_connection_layout.addWidget(self.k_tcp_address_input, 0, 1)

		kamikaze_connection_layout.addWidget(QLabel("Port:"), 0, 2)
		self.k_tcp_port_input = QSpinBox()
		self.k_tcp_port_input.setRange(1, 65535)
		self.k_tcp_port_input.setValue(14560)
		kamikaze_connection_layout.addWidget(self.k_tcp_port_input, 0, 3)

		k_connection_buttons_layout = QHBoxLayout()

		self.k_connect_btn = QPushButton("Connect")
		self.k_connect_btn.setStyleSheet("background-color: #4CAF50;")
		self.k_connect_btn.clicked.connect(self._on_connect_clicked)

		self.k_disconnect_btn = QPushButton("Disconnect")
		self.k_disconnect_btn.setStyleSheet("background-color: #F44336;")
		self.k_disconnect_btn.clicked.connect(self._on_disconnect_clicked)
		self.k_disconnect_btn.setEnabled(False)

		k_connection_buttons_layout.addWidget(self.k_connect_btn)
		k_connection_buttons_layout.addWidget(self.k_disconnect_btn)

		kamikaze_connection_layout.addLayout(k_connection_buttons_layout, 1, 0, 1, 4)

		connection_layout.addWidget(main_connection_group)
		connection_layout.addWidget(kamikaze_connection_group)
		connection_layout.addStretch()

		# 2. Basic Control Page
		basic_control_page = QWidget()
		basic_control_layout = QVBoxLayout(basic_control_page)
		basic_control_layout.setSpacing(15)

		# Page title
		basic_control_title = QLabel("Basic Drone Control")
		basic_control_title.setStyleSheet(
			"font-size: 24px; font-weight: bold; margin-bottom: 20px;"
		)
		basic_control_layout.addWidget(basic_control_title)

		# Status panel
		status_group = QGroupBox("Drone Status")
		status_layout = QGridLayout(status_group)

		self.armed_status_label = QLabel("Disarmed")
		self.flight_status_label = QLabel("Not Flying")
		self.position_label = QLabel("Position: N/A")
		self.altitude_label = QLabel("Altitude: N/A")
		self.battery_label = QLabel("Battery: N/A")

		status_layout.addWidget(QLabel("Armed:"), 0, 0)
		status_layout.addWidget(self.armed_status_label, 0, 1)
		status_layout.addWidget(QLabel("Flight:"), 0, 2)
		status_layout.addWidget(self.flight_status_label, 0, 3)
		status_layout.addWidget(QLabel("Position:"), 1, 0)
		status_layout.addWidget(self.position_label, 1, 1, 1, 3)
		status_layout.addWidget(QLabel("Altitude:"), 2, 0)
		status_layout.addWidget(self.altitude_label, 2, 1)
		status_layout.addWidget(QLabel("Battery:"), 2, 2)
		status_layout.addWidget(self.battery_label, 2, 3)

		# Flight control buttons
		control_group = QGroupBox("Flight Controls")
		control_layout = QVBoxLayout(control_group)

		# Arm/Disarm and takeoff/land buttons
		flight_controls_row1 = QHBoxLayout()

		self.arm_btn = QPushButton("Arm")
		self.arm_btn.setStyleSheet("background-color: #4CAF50;")
		self.arm_btn.clicked.connect(self._on_arm_clicked)
		self.arm_btn.setEnabled(False)

		self.disarm_btn = QPushButton("Disarm")
		self.disarm_btn.setStyleSheet("background-color: #F44336;")
		self.disarm_btn.clicked.connect(self._on_disarm_clicked)
		self.disarm_btn.setEnabled(False)

		self.takeoff_btn = QPushButton("Takeoff")
		self.takeoff_btn.setStyleSheet("background-color: #2196F3;")
		self.takeoff_btn.clicked.connect(self._on_takeoff_clicked)
		self.takeoff_btn.setEnabled(False)

		self.land_btn = QPushButton("Land")
		self.land_btn.setStyleSheet("background-color: #FF9800;")
		self.land_btn.clicked.connect(self._on_land_clicked)
		self.land_btn.setEnabled(False)

		self.rtl_btn = QPushButton("Return to Home")
		self.rtl_btn.setStyleSheet("background-color: #9C27B0;")
		self.rtl_btn.clicked.connect(self._on_rtl_clicked)
		self.rtl_btn.setEnabled(False)

		flight_controls_row1.addWidget(self.arm_btn)
		flight_controls_row1.addWidget(self.disarm_btn)
		flight_controls_row1.addWidget(self.takeoff_btn)
		flight_controls_row1.addWidget(self.land_btn)
		flight_controls_row1.addWidget(self.rtl_btn)

		# Takeoff altitude control
		takeoff_layout = QHBoxLayout()
		takeoff_layout.addWidget(QLabel("Takeoff Altitude (m):"))
		self.takeoff_alt_input = QDoubleSpinBox()
		self.takeoff_alt_input.setRange(1, 100)
		self.takeoff_alt_input.setValue(5.0)
		takeoff_layout.addWidget(self.takeoff_alt_input)
		takeoff_layout.addStretch()

		control_layout.addLayout(flight_controls_row1)
		control_layout.addLayout(takeoff_layout)

		# Go to position controls
		goto_group = QGroupBox("Go to Position")
		goto_layout = QGridLayout(goto_group)

		goto_layout.addWidget(QLabel("Latitude:"), 0, 0)
		self.goto_lat_input = QDoubleSpinBox()
		self.goto_lat_input.setRange(-90, 90)
		self.goto_lat_input.setDecimals(7)
		self.goto_lat_input.setSingleStep(0.0001)
		goto_layout.addWidget(self.goto_lat_input, 0, 1)

		goto_layout.addWidget(QLabel("Longitude:"), 0, 2)
		self.goto_lon_input = QDoubleSpinBox()
		self.goto_lon_input.setRange(-180, 180)
		self.goto_lon_input.setDecimals(7)
		self.goto_lon_input.setSingleStep(0.0001)
		goto_layout.addWidget(self.goto_lon_input, 0, 3)

		goto_layout.addWidget(QLabel("Altitude (m):"), 1, 0)
		self.goto_alt_input = QDoubleSpinBox()
		self.goto_alt_input.setRange(0, 500)
		self.goto_alt_input.setDecimals(1)
		self.goto_alt_input.setSingleStep(1.0)
		self.goto_alt_input.setValue(10.0)
		goto_layout.addWidget(self.goto_alt_input, 1, 1)

		self.goto_btn = QPushButton("Go")
		self.goto_btn.setStyleSheet("background-color: #2196F3;")
		self.goto_btn.clicked.connect(self._on_goto_clicked)
		self.goto_btn.setEnabled(False)
		goto_layout.addWidget(self.goto_btn, 1, 2, 1, 2)

		# Controller functions
		controller_group = QGroupBox("Payload Controls")
		controller_layout = QGridLayout(controller_group)

		self.drop_load_btn = QPushButton("Drop Load")
		self.drop_load_btn.setStyleSheet("background-color: #795548;")
		self.drop_load_btn.clicked.connect(self.drone_client.drop_load)

		self.pick_load_btn = QPushButton("Pick Load")
		self.pick_load_btn.setStyleSheet("background-color: #795548;")
		self.pick_load_btn.clicked.connect(self.drone_client.pick_load)

		self.raise_hook_btn = QPushButton("Raise Hook")
		self.raise_hook_btn.setStyleSheet("background-color: #795548;")
		self.raise_hook_btn.clicked.connect(self.drone_client.raise_hook)

		self.drop_hook_btn = QPushButton("Drop Hook")
		self.drop_hook_btn.setStyleSheet("background-color: #795548;")
		self.drop_hook_btn.clicked.connect(self.drone_client.drop_hook)

		self.kamikaze_btn = QPushButton("Kamikaze")
		self.kamikaze_btn.setStyleSheet("background-color: #F44336; font-weight: bold;")

		controller_layout.addWidget(self.drop_load_btn, 0, 0)
		controller_layout.addWidget(self.pick_load_btn, 0, 1)
		controller_layout.addWidget(self.raise_hook_btn, 0, 2)
		controller_layout.addWidget(self.drop_hook_btn, 1, 0)
		controller_layout.addWidget(self.kamikaze_btn, 1, 1, 1, 2)

		# Add all control groups to the layout
		basic_control_layout.addWidget(status_group)
		basic_control_layout.addWidget(control_group)
		basic_control_layout.addWidget(goto_group)
		basic_control_layout.addWidget(controller_group)
		basic_control_layout.addStretch()

		# 3. Mission Planning Page
		mission_page = QWidget()
		mission_layout = QVBoxLayout(mission_page)
		mission_layout.setSpacing(15)

		# Page title
		mission_title = QLabel("Mission Planning")
		mission_title.setStyleSheet(
			"font-size: 24px; font-weight: bold; margin-bottom: 20px;"
		)
		mission_layout.addWidget(mission_title)

		# Mission waypoints table
		mission_layout.addWidget(QLabel("Mission Waypoints:"))
		self.waypoint_table = MissionWaypointTable()
		self.waypoint_table.setStyleSheet("""
	        QTableWidget {
	            background-color: #222222;
	            alternate-background-color: #292929;
	            border: 1px solid #333333;
	        }
	        QTableWidget::item {
	            padding: 6px;
	        }
	        QHeaderView::section {
	            background-color: #333333;
	            color: white;
	            padding: 8px;
	            border: none;
	        }
	    """)
		mission_layout.addWidget(self.waypoint_table)

		# Add waypoint controls
		add_waypoint_group = QGroupBox("Add Waypoint")
		add_waypoint_layout = QGridLayout(add_waypoint_group)

		add_waypoint_layout.addWidget(QLabel("Latitude:"), 0, 0)
		self.waypoint_lat_input = QDoubleSpinBox()
		self.waypoint_lat_input.setRange(-90, 90)
		self.waypoint_lat_input.setDecimals(7)
		self.waypoint_lat_input.setSingleStep(0.0001)
		add_waypoint_layout.addWidget(self.waypoint_lat_input, 0, 1)

		add_waypoint_layout.addWidget(QLabel("Longitude:"), 0, 2)
		self.waypoint_lon_input = QDoubleSpinBox()
		self.waypoint_lon_input.setRange(-180, 180)
		self.waypoint_lon_input.setDecimals(7)
		self.waypoint_lon_input.setSingleStep(0.0001)
		add_waypoint_layout.addWidget(self.waypoint_lon_input, 0, 3)

		add_waypoint_layout.addWidget(QLabel("Altitude (m):"), 1, 0)
		self.waypoint_alt_input = QDoubleSpinBox()
		self.waypoint_alt_input.setRange(0, 500)
		self.waypoint_alt_input.setDecimals(1)
		self.waypoint_alt_input.setSingleStep(1.0)
		self.waypoint_alt_input.setValue(10.0)
		add_waypoint_layout.addWidget(self.waypoint_alt_input, 1, 1)

		add_waypoint_layout.addWidget(QLabel("Hold (s):"), 1, 2)
		self.waypoint_hold_input = QDoubleSpinBox()
		self.waypoint_hold_input.setRange(0, 60)
		self.waypoint_hold_input.setValue(10)
		self.waypoint_hold_input.setSingleStep(1)
		add_waypoint_layout.addWidget(self.waypoint_hold_input, 1, 3)

		self.add_waypoint_btn = QPushButton("Add Waypoint")
		self.add_waypoint_btn.setStyleSheet("background-color: #4CAF50;")
		self.add_waypoint_btn.clicked.connect(self._on_add_waypoint_clicked)
		add_waypoint_layout.addWidget(self.add_waypoint_btn, 2, 0, 1, 4)

		# Mission file operations
		file_operations_group = QGroupBox("File Operations")
		file_operations_layout = QHBoxLayout(file_operations_group)

		self.load_mission_btn = QPushButton("Load Mission")
		self.load_mission_btn.setStyleSheet("background-color: #607D8B;")
		self.load_mission_btn.clicked.connect(self._on_load_mission_clicked)

		self.save_mission_btn = QPushButton("Save Mission")
		self.save_mission_btn.setStyleSheet("background-color: #607D8B;")
		self.save_mission_btn.clicked.connect(self._on_save_mission_clicked)

		self.clear_mission_btn = QPushButton("Clear Mission")
		self.clear_mission_btn.setStyleSheet("background-color: #FF5722;")
		self.clear_mission_btn.clicked.connect(self._on_clear_mission_clicked)

		file_operations_layout.addWidget(self.load_mission_btn)
		file_operations_layout.addWidget(self.save_mission_btn)
		file_operations_layout.addWidget(self.clear_mission_btn)

		# Mission execution controls
		execution_group = QGroupBox("Mission Execution")
		execution_layout = QVBoxLayout(execution_group)

		buttons_layout = QHBoxLayout()

		self.upload_mission_btn = QPushButton("Upload Mission")
		self.upload_mission_btn.setStyleSheet("background-color: #2196F3;")
		self.upload_mission_btn.clicked.connect(self._on_upload_mission_clicked)
		self.upload_mission_btn.setEnabled(False)

		self.start_mission_btn = QPushButton("Start Mission")
		self.start_mission_btn.setStyleSheet("background-color: #4CAF50;")
		self.start_mission_btn.clicked.connect(self._on_start_mission_clicked)
		self.start_mission_btn.setEnabled(False)

		self.cancel_mission_btn = QPushButton("Cancel Mission")
		self.cancel_mission_btn.setStyleSheet("background-color: #F44336;")
		self.cancel_mission_btn.clicked.connect(self._on_cancel_mission_clicked)
		self.cancel_mission_btn.setEnabled(False)

		buttons_layout.addWidget(self.upload_mission_btn)
		buttons_layout.addWidget(self.start_mission_btn)
		buttons_layout.addWidget(self.cancel_mission_btn)

		mission_progress_layout = QHBoxLayout()
		mission_progress_layout.addWidget(QLabel("Mission Progress:"))
		self.mission_progress_bar = QProgressBar()
		self.mission_progress_bar.setRange(0, 100)
		mission_progress_layout.addWidget(self.mission_progress_bar)
		self.mission_status_label = QLabel("No mission active")
		mission_progress_layout.addWidget(self.mission_status_label)

		execution_layout.addLayout(buttons_layout)
		execution_layout.addLayout(mission_progress_layout)

		# Add mission groups to layout
		mission_layout.addWidget(add_waypoint_group)
		mission_layout.addWidget(file_operations_group)
		mission_layout.addWidget(execution_group)
		mission_layout.addStretch()

		# 4. Console Page
		console_page = QWidget()
		console_layout = QVBoxLayout(console_page)
		console_layout.setSpacing(15)

		# Page title
		console_title = QLabel("Console Output")
		console_title.setStyleSheet(
			"font-size: 24px; font-weight: bold; margin-bottom: 20px;"
		)
		console_layout.addWidget(console_title)

		self.console = ConsoleOutput()
		console_layout.addWidget(self.console)

		# 5. Authentication Page (Placeholder)
		auth_page = QWidget()
		auth_layout = QVBoxLayout(auth_page)
		auth_layout.setSpacing(15)

		# Page title
		auth_title = QLabel("Authentication")
		auth_title.setStyleSheet(
			"font-size: 24px; font-weight: bold; margin-bottom: 20px;"
		)
		auth_layout.addWidget(auth_title)

		# Login form
		auth_form_group = QGroupBox("User Login")
		auth_form_layout = QGridLayout(auth_form_group)

		auth_form_layout.addWidget(QLabel("Username:"), 0, 0)
		username_input = QLineEdit()
		auth_form_layout.addWidget(username_input, 0, 1)

		auth_form_layout.addWidget(QLabel("Password:"), 1, 0)
		password_input = QLineEdit()
		password_input.setEchoMode(QLineEdit.Password)
		auth_form_layout.addWidget(password_input, 1, 1)

		login_btn = QPushButton("Login")
		login_btn.setStyleSheet("background-color: #4CAF50;")
		auth_form_layout.addWidget(login_btn, 2, 0, 1, 2)

		auth_layout.addWidget(auth_form_group)
		auth_layout.addStretch()

		# Add all pages to stacked widget
		self.stacked_widget.addWidget(connection_page)
		self.stacked_widget.addWidget(basic_control_page)
		self.stacked_widget.addWidget(mission_page)
		self.stacked_widget.addWidget(console_page)
		self.stacked_widget.addWidget(auth_page)

		# Add the stacked widget to content layout
		content_layout.addWidget(self.stacked_widget)

		# Add nav and content to splitter
		nav_content_splitter.addWidget(nav_widget)
		nav_content_splitter.addWidget(content_widget)

		# Set splitter as main layout widget
		main_layout.addWidget(nav_content_splitter)

		# Set central widget
		self.setCentralWidget(main_widget)

		# Set default page
		self.stacked_widget.setCurrentIndex(0)

		# Update nav button styles to show selected state
		self.nav_connection_btn.setStyleSheet(
			"text-align: left; padding: 10px; background-color: #1E88E5;"
		)

		# Connect nav buttons to update selected styling
		self.nav_connection_btn.clicked.connect(
			lambda: self._update_nav_selection(self.nav_connection_btn)
		)
		self.nav_basic_control_btn.clicked.connect(
			lambda: self._update_nav_selection(self.nav_basic_control_btn)
		)
		self.nav_mission_btn.clicked.connect(
			lambda: self._update_nav_selection(self.nav_mission_btn)
		)
		self.nav_console_btn.clicked.connect(
			lambda: self._update_nav_selection(self.nav_console_btn)
		)
		self.nav_auth_btn.clicked.connect(
			lambda: self._update_nav_selection(self.nav_auth_btn)
		)

	def _update_nav_selection(self, selected_button):
		"""Update the styling of navigation buttons to show which is selected."""
		# Reset all buttons to default style
		for btn in [
			self.nav_connection_btn,
			self.nav_basic_control_btn,
			self.nav_mission_btn,
			self.nav_console_btn,
			self.nav_auth_btn,
		]:
			btn.setStyleSheet("text-align: left; padding: 10px;")

		# Set selected button style
		selected_button.setStyleSheet(
			"text-align: left; padding: 10px; background-color: #1E88E5;"
		)

	def _init_old_ui(self):
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
		self.connect_btn.clicked.connect(lambda: self._on_connect_clicked())
		self.connect_menu = QMenu(self)
		self.connect_action = self.connect_menu.addAction("Standard Connect")
		self.connect_action.triggered.connect(lambda: self._on_connect_clicked())
		self.tcp_connect_action = self.connect_menu.addAction("TCP Connect")
		self.tcp_connect_action.triggered.connect(
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
		self.kamikaze_btn = QPushButton("Kamikaze")
		self.kamikaze_btn.setStyleSheet("background-color: red;color: black;")

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
		basic_control_layout.addWidget(controller_group)

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

		self.console.append_message(f"Connecting to {_type}:{address}:{port}", "info")
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


def run_app(client):
	# parse command line arguments for simulation mode
	parser = argparse.ArgumentParser(description="Drone Control Center")
	parser.add_argument(
		"--is-simulation", action="store_true", help="Run in simulation mode"
	)
	args = parser.parse_args()
	is_simulation = args.is_simulation

	video_stream_window = CameraDisplay(title="Raw Stream")
	processed_stream_window = CameraDisplay(title="Processed Stream")
	window = DroneControlApp(
		client, video_stream_window, processed_stream_window, is_simulation
	)
	window.show()


def main():
	app = QApplication(sys.argv)
	"""Run the drone control application."""
	client = ZMQClient()
	client.start()
	run_app(client)
	sys.exit(app.exec())


if __name__ == "__main__":
	import argparse

	main()
