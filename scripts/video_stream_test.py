#!/usr/bin/env python3
import sys
import time
from typing import Optional
import logging
import subprocess
import queue
import json

import cv2
import numpy as np
import zmq
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QComboBox, QTextEdit,
    QGroupBox, QGridLayout, QLineEdit,
    QSplitter, QFrame
)
from PySide6.QtCore import QTimer, Signal, QThread, Signal, Qt
from PySide6.QtGui import QPixmap, QImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video-stream-test")


class RTSPWorker(QThread):
    """Worker thread for RTSP stream"""
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)
    
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = False
        self.cap = None
        
    def run(self):
        self.running = True
        try:
            # Try different backends for better RTSP support
            backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
            
            for backend in backends:
                self.cap = cv2.VideoCapture(self.rtsp_url, backend)
                if self.cap.isOpened():
                    logger.info(f"RTSP connected using backend: {backend}")
                    break
            else:
                raise Exception("Failed to connect to RTSP stream")
                
            # Configure for low latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.frame_ready.emit(frame)
                else:
                    time.sleep(0.01)
                    
        except Exception as e:
            self.error_occurred.emit(f"RTSP Error: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        self.running = False
        self.wait(3000)  # Wait up to 3 seconds


class ZMQWorker(QThread):
    """Worker thread for ZMQ streams"""
    frame_ready = Signal(np.ndarray)
    gps_data_ready = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, zmq_address: str, topic: str):
        super().__init__()
        self.zmq_address = zmq_address
        self.topic = topic.encode('utf-8')
        self.running = False
        self.context = None
        self.socket = None
        
    def run(self):
        self.running = True
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(self.zmq_address)
            self.socket.setsockopt(zmq.SUBSCRIBE, self.topic)
            self.socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            logger.info(f"ZMQ connected to {self.zmq_address}, topic: {self.topic}")
            
            while self.running:
                try:
                    # Receive multipart message
                    topic, data = self.socket.recv_multipart()
                    
                    # Decode JPEG frame
                    nparr = np.frombuffer(data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        self.frame_ready.emit(frame)
                        
                except zmq.Again:
                    # Timeout, continue
                    continue
                    
        except Exception as e:
            self.error_occurred.emit(f"ZMQ Error: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()
            if self.context:
                self.context.term()
    
    def stop(self):
        self.running = False
        self.wait(3000)


class ControlWorker(QThread):
    """Worker for ZMQ control commands"""
    response_ready = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, control_address: str):
        super().__init__()
        self.control_address = control_address
        self.command_queue = queue.Queue()
        self.running = False
        self.context = None
        self.socket = None
        
    def run(self):
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.control_address)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            self.running = True
            logger.info(f"Control connected to {self.control_address}")
            
            while self.running:
                try:
                    # Check for commands
                    try:
                        command = self.command_queue.get(timeout=0.1)
                        self.socket.send_string(command)
                        response = self.socket.recv_string()
                        self.response_ready.emit(f"Command: {command}\nResponse: {response}")
                    except queue.Empty:
                        continue
                        
                except zmq.Again:
                    continue
                    
        except Exception as e:
            self.error_occurred.emit(f"Control Error: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()
            if self.context:
                self.context.term()
    
    def send_command(self, command: str):
        """Queue a command to be sent"""
        try:
            self.command_queue.put_nowait(command)
        except queue.Full:
            logger.warning("Command queue full")
    
    def stop(self):
        self.running = False
        self.wait(3000)


class VideoStreamViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Stream Video Viewer")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #3c3c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0084ff;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #444444;
                border: 1px solid #666666;
                padding: 4px;
                border-radius: 4px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #666666;
                color: #ffffff;
                font-family: monospace;
            }
        """)
        
        # Worker threads
        self.video_worker = None
        self.control_worker = None
        
        # Current stream info
        self.current_stream = None
        self.fps_counter = 0
        self.fps_timer = time.time()
        
        # Setup UI
        self.setup_ui()
        
        # FPS timer
        self.fps_update_timer = QTimer()
        self.fps_update_timer.timeout.connect(self.update_fps_display)
        self.fps_update_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # Right panel - Video display
        video_panel = self.create_video_panel()
        splitter.addWidget(video_panel)
        
        # Set initial splitter sizes (30% control, 70% video)
        splitter.setSizes([400, 1000])
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_control_panel(self) -> QWidget:
        """Create the control panel"""
        panel = QFrame()
        panel.setMaximumWidth(450)
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Connection Settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QGridLayout(conn_group)
        
        # RTSP Settings
        conn_layout.addWidget(QLabel("RTSP URL:"), 0, 0)
        self.rtsp_url_edit = QLineEdit("rtsp://localhost:8554/live")
        conn_layout.addWidget(self.rtsp_url_edit, 0, 1)
        
        # ZMQ Settings
        conn_layout.addWidget(QLabel("ZMQ Video:"), 1, 0)
        self.zmq_video_edit = QLineEdit("tcp://localhost:5555")
        conn_layout.addWidget(self.zmq_video_edit, 1, 1)
        
        conn_layout.addWidget(QLabel("ZMQ Control:"), 2, 0)
        self.zmq_control_edit = QLineEdit("tcp://localhost:5556")
        conn_layout.addWidget(self.zmq_control_edit, 2, 1)
        
        layout.addWidget(conn_group)
        
        # Stream Selection
        stream_group = QGroupBox("Stream Selection")
        stream_layout = QVBoxLayout(stream_group)
        
        self.stream_combo = QComboBox()
        self.stream_combo.addItems([
            "Select Stream...",
            "RTSP - Raw Video (Fastest)",
            "ZMQ - Raw Video", 
            "ZMQ - Processed Video (with detection)"
        ])
        stream_layout.addWidget(self.stream_combo)
        
        # Connect/Disconnect buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        self.connect_btn.clicked.connect(self.connect_stream)
        self.disconnect_btn.clicked.connect(self.disconnect_stream)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        stream_layout.addLayout(button_layout)
        
        layout.addWidget(stream_group)
        
        # Stream Info
        info_group = QGroupBox("Stream Information")
        info_layout = QVBoxLayout(info_group)
        
        self.stream_info_label = QLabel("No stream connected")
        self.fps_label = QLabel("FPS: --")
        self.resolution_label = QLabel("Resolution: --")
        
        info_layout.addWidget(self.stream_info_label)
        info_layout.addWidget(self.fps_label)
        info_layout.addWidget(self.resolution_label)
        
        layout.addWidget(info_group)
        
        # Control Commands
        control_group = QGroupBox("Drone Control")
        control_layout = QVBoxLayout(control_group)
        
        # Quick command buttons
        commands = [
            ("Get Status", "STATUS"),
            ("Raise Hook", "RAISE_HOOK"),
            ("Drop Hook", "DROP_HOOK"),
            ("Get Helipad GPS", "HELIPAD_GPS"),
            ("Get Tank GPS", "TANK_GPS"),
        ]
        
        for name, command in commands:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, cmd=command: self.send_command(cmd))
            control_layout.addWidget(btn)
        
        layout.addWidget(control_group)
        
        # Response Log
        log_group = QGroupBox("Command Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)
        
        layout.addWidget(log_group)
        
        # Stretch to push everything to the top
        layout.addStretch()
        
        return panel
        
    def create_video_panel(self) -> QWidget:
        """Create the video display panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px solid #555555;
                border-radius: 8px;
                color: #888888;
                font-size: 18px;
            }
        """)
        self.video_label.setText("Select and connect to a video stream")
        self.video_label.setMinimumSize(640, 480)
        
        layout.addWidget(self.video_label)
        
        return panel
        
    def connect_stream(self):
        """Connect to selected stream"""
        stream_index = self.stream_combo.currentIndex()
        
        if stream_index == 0:
            self.log_message("Please select a stream type")
            return
            
        # Disconnect current stream
        self.disconnect_stream()
        
        try:
            if stream_index == 1:  # RTSP
                rtsp_url = self.rtsp_url_edit.text().strip()
                self.video_worker = RTSPWorker(rtsp_url)
                self.current_stream = f"RTSP: {rtsp_url}"
                
            elif stream_index == 2:  # ZMQ Raw
                zmq_url = self.zmq_video_edit.text().strip()
                self.video_worker = ZMQWorker(zmq_url, "video")
                self.current_stream = f"ZMQ Raw: {zmq_url}"
                
            elif stream_index == 3:  # ZMQ Processed
                zmq_url = self.zmq_video_edit.text().strip()
                self.video_worker = ZMQWorker(zmq_url, "processed_video")
                self.current_stream = f"ZMQ Processed: {zmq_url}"
            
            # Connect signals
            self.video_worker.frame_ready.connect(self.update_video_frame)
            self.video_worker.error_occurred.connect(self.handle_error)
            
            # Start worker
            self.video_worker.start()
            
            # Setup control worker if not already running
            if not self.control_worker or not self.control_worker.running:
                control_url = self.zmq_control_edit.text().strip()
                self.control_worker = ControlWorker(control_url)
                self.control_worker.response_ready.connect(self.handle_control_response)
                self.control_worker.error_occurred.connect(self.handle_error)
                self.control_worker.start()
            
            # Update UI
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.stream_info_label.setText(f"Connected: {self.current_stream}")
            self.statusBar().showMessage(f"Connected to {self.current_stream}")
            self.log_message(f"Connected to {self.current_stream}")
            
        except Exception as e:
            self.handle_error(f"Connection failed: {str(e)}")
            
    def disconnect_stream(self):
        """Disconnect current stream"""
        if self.video_worker:
            self.video_worker.stop()
            self.video_worker = None
            
        if self.control_worker:
            self.control_worker.stop()
            self.control_worker = None
            
        # Update UI
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.stream_info_label.setText("No stream connected")
        self.fps_label.setText("FPS: --")
        self.resolution_label.setText("Resolution: --")
        self.video_label.setText("Select and connect to a video stream")
        self.video_label.setPixmap(QPixmap())  # Clear video
        self.statusBar().showMessage("Disconnected")
        self.log_message("Disconnected from stream")
        
        # Reset FPS counter
        self.fps_counter = 0
        self.fps_timer = time.time()
        
    def update_video_frame(self, frame: np.ndarray):
        """Update video display with new frame"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width, channels = rgb_frame.shape
            
            # Update resolution display
            self.resolution_label.setText(f"Resolution: {width}x{height}")
            
            # Create QImage
            bytes_per_line = channels * width
            qt_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Scale to fit label while maintaining aspect ratio
            label_size = self.video_label.size()
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
            
            # Update FPS counter
            self.fps_counter += 1
            
        except Exception as e:
            logger.error(f"Error updating video frame: {e}")
            
    def update_fps_display(self):
        """Update FPS display"""
        current_time = time.time()
        elapsed = current_time - self.fps_timer
        
        if elapsed >= 1.0 and self.fps_counter > 0:
            fps = self.fps_counter / elapsed
            self.fps_label.setText(f"FPS: {fps:.1f}")
            self.fps_counter = 0
            self.fps_timer = current_time
            
    def send_command(self, command: str):
        """Send control command"""
        if self.control_worker and self.control_worker.running:
            self.control_worker.send_command(command)
            self.log_message(f"Sent command: {command}")
        else:
            self.log_message("Control connection not available")
            
    def handle_control_response(self, response: str):
        """Handle control command response"""
        self.log_message(response)
        
    def handle_error(self, error_msg: str):
        """Handle errors"""
        self.log_message(f"ERROR: {error_msg}")
        self.statusBar().showMessage(f"Error: {error_msg}")
        logger.error(error_msg)
        
    def log_message(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.log_text.append(formatted_msg)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def closeEvent(self, event):
        """Handle window close"""
        self.disconnect_stream()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Video Stream Viewer")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    viewer = VideoStreamViewer()
    viewer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
