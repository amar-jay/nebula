"""
Mission Worker Thread for Sequential Load Operations

This module provides a worker thread that handles sequential pick load and drop load
operations with timeout handling and mission resumption.
"""

import time
from threading import Thread, Event, Lock
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from src.mq.crane import ZMQTopics
from src.gcs.drone_client import DroneClient

class MissionWorker(QObject):
    """
    Worker thread for handling sequential load operations during missions.
    
    This worker handles pick load and drop load operations with a 10-second timeout.
    If an operation takes longer than 10 seconds, it's ignored and the mission is resumed.
    The operations toggle between pick load and drop load on consecutive resume mission calls.
    """
    
    # Signals
    operation_started = Signal(str)  # Emitted when an operation starts
    operation_completed = Signal(str, bool)  # Emitted when operation completes (operation, success)
    operation_timeout = Signal(str)  # Emitted when operation times out
    mission_resumed = Signal()  # Emitted when mission is resumed
    timeout_requested = Signal(int)  # Request to start timeout timer
    timeout_cancel_requested = Signal()  # Request to cancel timeout timer
    progress_update = Signal(int, str)  # Progress percentage and status message

    def __init__(self, drone_client:DroneClient, logger: Optional[Callable] = None):
        super().__init__()
        self.drone_client = drone_client
        self.logger = logger or self._default_logger
        
        # State management
        self._current_operation = None
        self._next_operation = ZMQTopics.PICK_LOAD  # Start with pick load
        self._operation_lock = Lock()
        self._worker_thread = None
        self._stop_event = Event()
        
        # Timeout timer
        self._timeout_timer = QTimer(self)
        self._timeout_timer.timeout.connect(self._handle_timeout)
        self._timeout_timer.setSingleShot(True)
        
        # Connect internal signals for thread-safe timer operations
        self.timeout_requested.connect(self._start_timeout_timer)
        self.timeout_cancel_requested.connect(self._cancel_timeout_timer)
        
        # Operation tracking
        self._operation_start_time = None
        
    def _default_logger(self, message: str, level: str = "info"):
        """Default logger that prints to console"""
        print(f"[MissionWorker] {message} ({level})")
        
    def _log(self, message: str, level: str = "info"):
        """Internal logging method"""
        self.logger(f"MissionWorker: {message}", level)
        
    def start_sequential_operation(self):
        """
        Start a sequential load operation (pick load or drop load).
        This method is called when the resume mission button is enabled.
        """
        with self._operation_lock:
            if self._current_operation is not None:
                self._log("Operation already in progress, skipping", "warning")
                return
                
            # Determine the next operation
            operation = self._next_operation
            self._current_operation = operation
            
            # Toggle for next time
            if self._next_operation == ZMQTopics.PICK_LOAD:
                self._next_operation = ZMQTopics.DROP_LOAD
            else:
                self._next_operation = ZMQTopics.PICK_LOAD

        # Start the operation in a separate thread
        self._worker_thread = Thread(target=self._execute_operation, args=(operation,))
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
        # Start timeout timer (10 seconds)
        self._operation_start_time = time.time()
        self.timeout_requested.emit(130000)  # 130 seconds - emit signal for thread safety
        
        self._log(f"Started {operation.value} operation")
        self.operation_started.emit(operation.value)
        
    def _execute_operation(self, operation: ZMQTopics):
        """
        Execute the specified load operation.
        
        Args:
            operation: The type of operation to execute
        """
        try:
            success = False

            if operation == ZMQTopics.PICK_LOAD:
                # Execute pick load
                result = self.drone_client.pick_load()
                success = result is not False  # Consider None or True as success

            elif operation == ZMQTopics.DROP_LOAD:
                # Execute drop load
                result = self.drone_client.drop_load()
                success = result is not False  # Consider None or True as success
            
            # If we get here, operation completed before timeout
            if not self._stop_event.is_set():
                self._complete_operation(operation, success)
                
        except Exception as e:
            self._log(f"Error during {operation.value}: {e}", "error")
            if not self._stop_event.is_set():
                self._complete_operation(operation, False)

    def _complete_operation(self, operation: ZMQTopics, success: bool):
        """
        Handle operation completion.
        
        Args:
            operation: The completed operation
            success: Whether the operation was successful
        """
        with self._operation_lock:
            if self._current_operation != operation:
                return  # Operation was already handled (probably timed out)
                
            # Stop timeout timer using signal for thread safety
            self.timeout_cancel_requested.emit()
            
            # Clear current operation
            self._current_operation = None
            
            # Calculate execution time
            execution_time = time.time() - self._operation_start_time if self._operation_start_time else 0
            
            self._log(f"Completed {operation.value} in {execution_time:.2f}s (success: {success})")
            self.operation_completed.emit(operation.value, success)
            
            # Resume mission regardless of operation success
            self._resume_mission()
            
    def _handle_timeout(self):
        """Handle operation timeout"""
        with self._operation_lock:
            if self._current_operation is None:
                return  # No operation in progress
                
            operation = self._current_operation
            self._current_operation = None
            
            self._log(f"Operation {operation.value} timed out after 10 seconds", "warning")
            self.operation_timeout.emit(operation.value)
            
            # Stop the worker thread
            self._stop_event.set()
            
            # Resume mission despite timeout
            self._resume_mission()
            
    def _resume_mission(self):
        """Resume the drone mission"""
        try:
            result = self.drone_client.resume_mission()
            if result is not False:
                self._log("Mission resumed successfully")
                self.mission_resumed.emit()
            else:
                self._log("Failed to resume mission", "error")
        except Exception as e:
            self._log(f"Error resuming mission: {e}", "error")
            
    def reset_operation_sequence(self):
        """Reset the operation sequence to start with pick load"""
        with self._operation_lock:
            self._next_operation = ZMQTopics.PICK_LOAD
            self._log("Reset operation sequence to start with pick load")
            
    def get_next_operation(self) -> str:
        """Get the next operation that will be executed"""
        return self._next_operation.value
        
    def is_operation_in_progress(self) -> bool:
        """Check if an operation is currently in progress"""
        with self._operation_lock:
            return self._current_operation is not None
    
    def _start_timeout_timer(self, timeout_ms: int):
        """Start the timeout timer (thread-safe, called from main thread)"""
        self._timeout_timer.start(timeout_ms)
        
    def _cancel_timeout_timer(self):
        """Cancel the timeout timer (thread-safe, called from main thread)"""
        if self._timeout_timer.isActive():
            self._timeout_timer.stop()
            
    def stop(self):
        """Stop the worker and clean up resources"""
        self._stop_event.set()
        self.timeout_cancel_requested.emit()  # Use signal for thread safety
        
        with self._operation_lock:
            self._current_operation = None
            
        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
            
        self._log("Mission worker stopped")


class MissionWorkerManager(QObject):
    """
    Manager class for the mission worker to integrate with the main application.
    """
    
    # Expose signals for UI integration
    operation_started = Signal(str)
    operation_completed = Signal(str, bool)
    operation_timeout = Signal(str)
    mission_resumed = Signal()
    progress_update = Signal(int, str)  # Progress percentage and status message
    
    def __init__(self, drone_client, logger: Optional[Callable] = None):
        super().__init__()
        self.drone_client = drone_client
        self.logger = logger
        self.worker = None
        
    def initialize_worker(self):
        """Initialize the mission worker"""
        if self.worker is None:
            self.worker = MissionWorker(self.drone_client, self.logger)
            
            # Connect signals and forward them to manager signals for UI updates
            self.worker.operation_started.connect(self._on_operation_started)
            self.worker.operation_started.connect(self.operation_started.emit)
            
            self.worker.operation_completed.connect(self._on_operation_completed)
            self.worker.operation_completed.connect(self.operation_completed.emit)
            
            self.worker.operation_timeout.connect(self._on_operation_timeout)
            self.worker.operation_timeout.connect(self.operation_timeout.emit)
            
            self.worker.mission_resumed.connect(self._on_mission_resumed)
            self.worker.mission_resumed.connect(self.mission_resumed.emit)
            
            self.worker.progress_update.connect(self.progress_update.emit)
            
    def start_sequential_operation(self):
        """Start a sequential operation via the worker"""
        if self.worker is None:
            self.initialize_worker()
        self.worker.start_sequential_operation()
        
    def reset_sequence(self):
        """Reset the operation sequence"""
        if self.worker:
            self.worker.reset_operation_sequence()
            
    def get_next_operation(self) -> str:
        """Get the next operation"""
        if self.worker:
            return self.worker.get_next_operation()
        return ZMQTopics.PICK_LOAD.value
        
    def is_busy(self) -> bool:
        """Check if worker is busy"""
        if self.worker:
            return self.worker.is_operation_in_progress()
        return False
        
    def cleanup(self):
        """Clean up the worker"""
        if self.worker:
            self.worker.stop()
            self.worker = None
            
    def _on_operation_started(self, operation: str):
        """Handle operation started signal"""
        if self.logger:
            self.logger(f"Started {operation} operation", "info")
            
    def _on_operation_completed(self, operation: str, success: bool):
        """Handle operation completed signal"""
        status = "successfully" if success else "with errors"
        if self.logger:
            self.logger(f"Completed {operation} {status}", "success" if success else "warning")
            
    def _on_operation_timeout(self, operation: str):
        """Handle operation timeout signal"""
        if self.logger:
            self.logger(f"Operation {operation} timed out after 10 seconds", "warning")
            
    def _on_mission_resumed(self):
        """Handle mission resumed signal"""
        if self.logger:
            self.logger("Mission resumed after load operation", "info")


class KamikazeWorker(QObject):
    """
    Worker thread for handling the kamikaze sequence operations.
    
    This worker handles the entire kamikaze sequence without blocking the UI thread:
    1. Set mode to GUIDED
    2. Arm the drone
    3. Takeoff to specified altitude
    4. Navigate to target coordinates
    5. Execute kamikaze strike
    6. Land the drone
    """
    
    # Signals
    sequence_started = Signal()
    step_completed = Signal(str, bool)  # step_name, success
    sequence_completed = Signal(bool)  # overall_success
    sequence_failed = Signal(str)  # error_message
    progress_update = Signal(int, str)  # progress_percentage, current_step

    def __init__(self, drone_client: DroneClient, logger: Optional[Callable] = None):
        super().__init__()
        self.drone_client = drone_client
        self.logger = logger or self._default_logger
        
        # State management
        self._worker_thread = None
        self._stop_event = Event()
        self._operation_lock = Lock()
        self._is_running = False
        
    def _default_logger(self, message: str, level: str = "info"):
        """Default logger that prints to console"""
        print(f"[KamikazeWorker] {message} ({level})")
        
    def _log(self, message: str, level: str = "info"):
        """Internal logging method"""
        self.logger(f"KamikazeWorker: {message}", level)
        
    def start_kamikaze_sequence(self, target_coordinates: Tuple[float, float], takeoff_altitude: float = 10.0):
        """
        Start the kamikaze sequence in a worker thread.
        
        Args:
            target_coordinates: (latitude, longitude) of the target
            takeoff_altitude: Altitude to takeoff to in meters
        """
        with self._operation_lock:
            if self._is_running:
                self._log("Kamikaze sequence already in progress", "warning")
                return False
                
            self._is_running = True
            self._stop_event.clear()

        # Start the sequence in a separate thread
        self._worker_thread = Thread(
            target=self._execute_kamikaze_sequence, 
            args=(target_coordinates, takeoff_altitude)
        )
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
        self._log("Started kamikaze sequence")
        self.sequence_started.emit()
        return True
        
    def _execute_kamikaze_sequence(self, target_coordinates: Tuple[float, float], takeoff_altitude: float):
        """
        Execute the full kamikaze sequence.
        
        Args:
            target_coordinates: (latitude, longitude) of the target
            takeoff_altitude: Altitude to takeoff to in meters
        """
        try:
            steps = [
                ("Setting GUIDED mode", lambda: self._set_guided_mode()),
                ("Arming drone", lambda: self._arm_drone()),
                ("Taking off", lambda: self._takeoff(takeoff_altitude)),
                ("Executing kamikaze strike", lambda: self._execute_kamikaze(target_coordinates)),
                ("Activating payload", lambda: self._activate_payload()),
                ("Landing drone", lambda: self._land_drone())
            ]
            
            total_steps = len(steps)
            
            for i, (step_name, step_function) in enumerate(steps):
                if self._stop_event.is_set():
                    self._log("Kamikaze sequence cancelled", "warning")
                    return
                    
                self._log(f"Executing step: {step_name}")
                progress = int((i / total_steps) * 100)
                self.progress_update.emit(progress, step_name)
                
                try:
                    success = step_function()
                    self.step_completed.emit(step_name, success)
                    
                    if not success:
                        error_msg = f"Failed at step: {step_name}"
                        self._log(error_msg, "error")
                        self.sequence_failed.emit(error_msg)
                        return
                        
                except Exception as e:
                    error_msg = f"Error during {step_name}: {str(e)}"
                    self._log(error_msg, "error")
                    self.sequence_failed.emit(error_msg)
                    return
                    
                # Small delay between steps
                time.sleep(1)
            
            # Sequence completed successfully
            self.progress_update.emit(100, "Kamikaze sequence completed")
            self._log("Kamikaze sequence completed successfully", "success")
            self.sequence_completed.emit(True)
            
        except Exception as e:
            error_msg = f"Unexpected error in kamikaze sequence: {str(e)}"
            self._log(error_msg, "error")
            self.sequence_failed.emit(error_msg)
        finally:
            with self._operation_lock:
                self._is_running = False
                
    def _set_guided_mode(self) -> bool:
        """Set drone to GUIDED mode"""
        try:
            if self.drone_client.kamikaze_connection:
                self.drone_client.kamikaze_connection.set_mode('GUIDED')
                time.sleep(1)  # Wait for mode change
                return True
            return False
        except Exception as e:
            print(e)
            self._log(f"Failed to set GUIDED mode: {e}", "error")
            return False
            
    def _arm_drone(self) -> bool:
        """Arm the kamikaze drone"""
        try:
            if self.drone_client.kamikaze_connection:
                self.drone_client.kamikaze_connection.arm()
                time.sleep(1)  # Wait for arming
                return True
            return False
        except Exception as e:
            self._log(f"Failed to arm drone: {e}", "error")
            return False
            
    def _takeoff(self, altitude: float) -> bool:
        """Takeoff to specified altitude"""
        try:
            if self.drone_client.kamikaze_connection:
                self.drone_client.kamikaze_connection.takeoff(altitude)
                # Wait for takeoff to complete (could add more sophisticated monitoring)
                time.sleep(5)
                return True
            return False
        except Exception as e:
            self._log(f"Failed to takeoff: {e}", "error")
            return False
            
    def _execute_kamikaze(self, target_coordinates: Tuple[float, float]) -> bool:
        """Execute the kamikaze strike"""
        try:
            result = self.drone_client.kamikaze()
            time.sleep(2)  # Wait for kamikaze to initiate
            return result is not False
        except Exception as e:
            self._log(f"Failed to execute kamikaze: {e}", "error")
            return False
            
    def _activate_payload(self) -> bool:
        """Activate the payload (repeat relay)"""
        try:
            if self.drone_client.kamikaze_connection:
                self.drone_client.kamikaze_connection.repeat_relay(count=4, delay=5)
                time.sleep(5)  # Wait for payload activation
                return True
            return False
        except Exception as e:
            self._log(f"Failed to activate payload: {e}", "error")
            return False
            
    def _land_drone(self) -> bool:
        """Land the drone"""
        try:
            if self.drone_client.kamikaze_connection:
                self.drone_client.kamikaze_connection.land()
                time.sleep(3)  # Wait for landing to initiate
                return True
            return False
        except Exception as e:
            self._log(f"Failed to land drone: {e}", "error")
            return False
            
    def stop(self):
        """Stop the kamikaze sequence"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        with self._operation_lock:
            self._is_running = False
            
    def is_running(self) -> bool:
        """Check if kamikaze sequence is currently running"""
        with self._operation_lock:
            return self._is_running


class KamikazeWorkerManager(QObject):
    """
    Manager for the kamikaze worker that provides a simple interface for the UI.
    """
    
    # Expose worker signals through the manager
    sequence_started = Signal()
    step_completed = Signal(str, bool)
    sequence_completed = Signal(bool)
    sequence_failed = Signal(str)
    progress_update = Signal(int, str)
    
    def __init__(self, drone_client: DroneClient, logger: Optional[Callable] = None):
        super().__init__()
        self.drone_client = drone_client
        self.logger = logger
        self.worker = None
        
    def initialize_worker(self):
        """Initialize the kamikaze worker"""
        self.worker = KamikazeWorker(self.drone_client, self.logger)
        
        # Connect worker signals to manager signals to relay them
        self.worker.sequence_started.connect(self.sequence_started.emit)
        self.worker.step_completed.connect(self.step_completed.emit)
        self.worker.sequence_completed.connect(self.sequence_completed.emit)
        self.worker.sequence_failed.connect(self.sequence_failed.emit)
        self.worker.progress_update.connect(self.progress_update.emit)
        
        # Connect signals for internal logging if logger is available
        if self.logger:
            self.worker.sequence_started.connect(self._on_sequence_started)
            self.worker.step_completed.connect(self._on_step_completed)
            self.worker.sequence_completed.connect(self._on_sequence_completed)
            self.worker.sequence_failed.connect(self._on_sequence_failed)
            self.worker.progress_update.connect(self._on_progress_update)
            
    def start_kamikaze(self, target_coordinates: Tuple[float, float], takeoff_altitude: float = 10.0) -> bool:
        """
        Start the kamikaze sequence.
        
        Args:
            target_coordinates: (latitude, longitude) of the target
            takeoff_altitude: Altitude to takeoff to in meters
            
        Returns:
            bool: True if sequence started successfully, False otherwise
        """
        if not self.worker:
            self.initialize_worker()
            
        return self.worker.start_kamikaze_sequence(target_coordinates, takeoff_altitude)
        
    def stop_kamikaze(self):
        """Stop the kamikaze sequence"""
        if self.worker:
            self.worker.stop()
            
    def is_running(self) -> bool:
        """Check if kamikaze sequence is currently running"""
        if self.worker:
            return self.worker.is_running()
        return False
        
    def cleanup(self):
        """Clean up the worker"""
        if self.worker:
            self.worker.stop()
            self.worker = None
            
    def _on_sequence_started(self):
        """Handle sequence started signal"""
        if self.logger:
            self.logger("Kamikaze sequence started", "info")
            
    def _on_step_completed(self, step_name: str, success: bool):
        """Handle step completed signal"""
        status = "completed" if success else "failed"
        level = "success" if success else "error"
        if self.logger:
            self.logger(f"Kamikaze step '{step_name}' {status}", level)
            
    def _on_sequence_completed(self, success: bool):
        """Handle sequence completed signal"""
        status = "successfully completed" if success else "completed with errors"
        level = "success" if success else "warning"
        if self.logger:
            self.logger(f"Kamikaze sequence {status}", level)
            
    def _on_sequence_failed(self, error_message: str):
        """Handle sequence failed signal"""
        if self.logger:
            self.logger(f"Kamikaze sequence failed: {error_message}", "error")
            
    def _on_progress_update(self, progress: int, step_name: str):
        """Handle progress update signal"""
        if self.logger:
            self.logger(f"Kamikaze progress: {progress}% - {step_name}", "info")

