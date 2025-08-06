# FOR TESTING PURPOSES ONLY
from logging import currentframe
import traceback
import os
import time
from typing import Optional, Tuple

import cv2
import math
import numpy as np

from src.controls.mavlink import ardupilot
from src.controls.detection import yolo
from src.controls.mavlink.ardupilot import Waypoint
from src.controls.mavlink.gz import GazeboVideoCapture, enable_streaming

# Mission constants
HELIPAD_CLASS = "helipad"
DETECTION_THRESHOLD = 0.5
HOLD_TIME = 60
REPOSITION_TIMEOUT = 30
FRAME_DELAY = 0.05

# Camera intrinsic matrix
CAMERA_MATRIX = np.array(
    [[205.46962738037109, 0.0, 320], [0.0, 205.46965599060059, 240], [0.0, 0.0, 1.0]]
)

class STATES:
    IN_FLIGHT = 0
    HOLD = 1
    STABILIZE = 2
    REACHED = 3
    SIMULATED_CRANE_HOLD = 4
current_waypoint = 0
current_state = STATES.IN_FLIGHT
hold_timer = None
detected_coords = None
stable_coords = None

class MissionDisplay:
    """Handles the visual display of drone mission progress"""

    def __init__(self, window_name: str = "Drone Mission"):
        self.window_name = window_name
        self.flight_mode = "AUTO"

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 720)

    def set_flight_mode(self, mode: str):
        """Update the current flight mode display"""
        self.flight_mode = mode

    def update_display(
        self,
        frame: np.ndarray,
        annotated_frame: np.ndarray,
        current_gps: Tuple[float, float, float],
        detected_coords: Optional[Tuple[float, float]] = None,
        center_offset: Optional[Tuple[float, float]] = None,
        actual_coords: Optional[Tuple[float, float, float]] = None,
        gps_error: Optional[float] = None,
    ) -> int:
        """Update the display with current mission status"""

        # Create side-by-side display
        h, w = frame.shape[:2]
        display_frame = np.zeros((h, w * 2, 3), dtype=np.uint8)
        display_frame[:, :w] = frame
        display_frame[:, w:] = annotated_frame

        # Add separator line
        cv2.line(display_frame, (w, 0), (w, h), (255, 255, 255), 2)

        # Add frame labels
        self._add_text(display_frame, "Raw Feed", (10, 30), (0, 255, 0))
        self._add_text(display_frame, "Annotated Feed", (w + 10, 30), (0, 255, 0))

        # Add flight mode with color coding
        mode_color = self._get_mode_color(self.flight_mode)
        self._add_text(
            display_frame, f"MODE: {self.flight_mode}", (w - 200, 30), mode_color
        )

        # Add GPS information
        self._add_gps_info(
            display_frame,
            current_gps,
            detected_coords,
            center_offset,
            actual_coords,
            gps_error,
            w,
            h,
        )

        # Display and return key press
        cv2.imshow(self.window_name, display_frame)
        return cv2.waitKey(5) & 0xFF

    def _add_text(
        self,
        frame: np.ndarray,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int],
    ):
        """Add text to the frame"""
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def _get_mode_color(self, mode: str) -> Tuple[int, int, int]:
        """Get color for flight mode display"""
        colors = {
            "HOLD": (0, 165, 255),  # Orange
            "STABILIZE": (80, 80, 255),  # Red
            "AUTO": (0, 255, 0),  # Green
            "REACHED": (255, 80,  80),  # Green
            "LOADING CARGO": (255, 165,  0) 
        }
        return colors.get(mode, (255, 255, 255))  # White default

    def _add_gps_info(
        self,
        frame: np.ndarray,
        current_gps: Tuple[float, float, float],
        detected_coords: Optional[Tuple[float, float]],
        center_offset: Optional[Tuple[float, float]],
        actual_coords: Optional[Tuple[float, float, float]],
        gps_error: Optional[float],
        w: int,
        h: int,
    ):
        """Add GPS and detection information to display"""

        # Current GPS position
        if actual_coords:
            self._add_text(
                frame,
                f"Actual GPS: {actual_coords[0]:.8f}, {actual_coords[1]:.8f}",
                (10, h - 30),
                (0, 255, 0),
            )

        # Detection information
        if detected_coords and center_offset:
            self._add_text(
                frame,
                f"Detected GPS: {detected_coords[0]:.8f}, {detected_coords[1]:.8f}",
                (10, h - 60),
                (255, 165, 0),
            )
            self._add_text(
                frame,
                f"Center Offset: ({center_offset[0]:.1f}, {center_offset[1]:.1f})",
                (10, h - 90),
                (0, 165, 255),
            )
            def _haversine(first, second):
                R = 6371000

                phi = math.radians(first[0])
                phi2 = math.radians(second[0])
                dphi = math.radians(second[0] - first[0])
                dlambda = math.radians(second[1] - first[1])

                a = math.sin(dphi / 2) ** 2 + math.cos(phi) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
                c = 2* math.atan2(math.sqrt(a), math.sqrt(1-a))

                return R*c

            # Error calculations
            if actual_coords:
                curr_diff = _haversine(current_gps, actual_coords)
                pred_diff = _haversine(current_gps, detected_coords)
                detection_diff = _haversine(actual_coords, detected_coords)

                self._add_text(
                    frame,
                    f"Current Distance: {curr_diff:.8f}m",
                    (w + 10, h - 90),
                    (0, 255, 0),
                )
                self._add_text(
                    frame,
                    f"Predicted Distance: {pred_diff:.8f}m",
                    (w + 10, h - 60),
                    (0, 255, 0),
                )

                error_text = (
                    f"Detection Error: {detection_diff:.8f}m"
                )
                if gps_error:
                    error_text += f" | {gps_error:.2f}m"
                self._add_text(frame, error_text, (w + 10, h - 30), (255, 165, 0))
        else:
            self._add_text(frame, "No helipad detected", (10, h - 60), (0, 0, 255))

def stabilize_after_reached(waypoint_seq: int, completed: bool):
    global current_waypoint, current_state, hold_timer, stable_coords
    """Handle waypoint reached event with helipad detection and repositioning"""
    if current_state == STATES.IN_FLIGHT:
        if completed or waypoint_seq <= current_waypoint:
            return

        # Switch to guided mode for precision maneuvers
        connection.set_mode("GUIDED")
        display.set_flight_mode("HOLD")
        hold_timer = time.time()
        current_state = STATES.HOLD
    elif current_state == STATES.HOLD:
        # if in hold
        if not hold_timer:
            raise Exception("Something wrong with hold timer")
        if time.time() - hold_timer > HOLD_TIME / 2:
            connection.log("held still enough")
            current_state = STATES.STABILIZE
            hold_timer = None
        else:
            stable_coords = detected_coords
    elif current_state == STATES.STABILIZE:
        if not detected_coords:
            connection.log("⚠️ No helipad detected, continuing mission")
            goto = mission_coords[current_waypoint]
            goto.alt += 5
            if hold_timer is None:
                connection.goto_waypointv2(**goto.__dict__)
                hold_timer = time.time()
            elif time.time() - hold_timer > HOLD_TIME:
                hold_timer = None
        else:
            connection.log("📸 Stabilizing on helipad...")
            if not stable_coords:
                raise Exception("Cannot stabilize since there is no stable point")
            connection.goto_waypointv2(stable_coords[0],stable_coords[1], 10)
            current_state = STATES.SIMULATED_CRANE_HOLD
            hold_timer = time.time()
    elif current_state == STATES.SIMULATED_CRANE_HOLD:
        display.set_flight_mode("LOADING CARGO")
        if time.time() - hold_timer > HOLD_TIME:
            display.set_flight_mode("REACHED")
            current_state = STATES.REACHED
    elif current_state == STATES.REACHED:
        if not stable_coords:
            raise Exception("How did you end up in this state STATES.REACHED.")
        if connection.check_reposition_reached(stable_coords[0],stable_coords[1], 10):
            connection.log(f"🎯 Reached waypoint {waypoint_seq}")
            connection.set_mode("AUTO")
            display.set_flight_mode("AUTO")
            current_waypoint = waypoint_seq
            current_state = STATES.IN_FLIGHT
            connection.log("✅ Resumed AUTO mode")


def process_single_frame(
    actual_coords: Optional[Tuple[float, float, float]] = None
) -> bool:
    global detected_coords
    """Process one frame from camera and update display"""
    ret, frame = camera.read()
    if not ret:
        connection.log("❌ Failed to capture frame")
        return False
    # Get current drone state
    current_gps = connection.get_amsl_gps_location()
    if current_gps is None:
        return False
    current_attitude = connection.get_current_attitude()
    if current_attitude is None:
        return False
    drone_gps = current_gps[:3]
    # Process frame for helipad detection
    annotated_frame, _coords, center_offset = estimator.process_frame(
        frame=frame,
        drone_gps=drone_gps,
        drone_attitude=current_attitude,
        ground_level_masl=current_gps[3] - current_gps[2],
        object_classes=[HELIPAD_CLASS],
        threshold=DETECTION_THRESHOLD,
    )
    helipad = _coords.get("helipad", None)
    pixel = center_offset.get("helipad", None)
    if helipad is not None:
        detected_coords = helipad
    # Collect dataset if enabled and helipad detected
    if (
        helipad
        and pixel
        and actual_coords
    ):
        _collect_dataset_sample(
            pixel, actual_coords[:2], drone_gps, current_attitude
        )

    # Update display
    display.update_display(
        frame=frame,
        annotated_frame=annotated_frame,
        current_gps=drone_gps,
        detected_coords=helipad,
        center_offset=pixel,
        actual_coords=actual_coords,
    )
    return True

def _collect_dataset_sample(
    pixel_coords: Tuple[float, float],
    true_gps: Tuple[float, float],
    drone_gps: Tuple[float, float, float],
    drone_attitude: Tuple[float, float, float],
):
    """Collect a single dataset sample"""
    try:
        # Format the data for CSV
        pixel_str = f"{pixel_coords[0]:.2f},{pixel_coords[1]:.2f}"
        gps_true_str = f"{true_gps[0]:.8f},{true_gps[1]:.8f}"
        drone_gps_str = f"{drone_gps[0]:.8f},{drone_gps[1]:.8f},{drone_gps[2]:.2f}"
        drone_attitude_str = f"{drone_attitude[0]:.4f},{drone_attitude[1]:.4f},{drone_attitude[2]:.4f}"

        # Write to CSV
        dataset_writer.writerow(
            [pixel_str, gps_true_str, drone_gps_str, drone_attitude_str]
        )

    except Exception as e:
        connection.log(f"❌ Dataset collection error: {e}")

connection = ardupilot.ArdupilotConnection("udp:127.0.0.1:14550")
camera = cv2.VideoCapture("/home/amarjay/Desktop/drone-gimbal-raw.mp4")
if not camera.isOpened():
    connection.log("❌ Failed to open camera stream")
    exit(1)
display = MissionDisplay("Multiple Waypoint Stabilized Landing Test")
estimator = yolo.YoloObjectTracker(
    model_path=os.path.join(os.path.dirname(__file__), "detection/best_v2.pt"),
    K=CAMERA_MATRIX,
)
dataset_writer_context = estimator.dataset_writer("multi_stabilization_test.csv")

try:
    enable_streaming()
    # Setup camera streaming
    dataset_writer = dataset_writer_context.__enter__()

    connection.set_mode("GUIDED")
    connection.arm()

    connection.takeoff(10)

    current_pos = connection.get_relative_gps_location()
    if not current_pos:
        print("cannot fetch position")
        exit(1)
    lat, lon, alt = current_pos

    mission_coords = [
        Waypoint(lat=lat + 0.0008, lon=lon + 0.00003, alt=10, hold=10),
        # Waypoint(lat - 0.00004, lon - 0.00012, 15),
        # Waypoint(lat, lon + 0.000008, 10),
        # Waypoint(lat - 0.00001, lon - 0.00011, 7.5),
        # Waypoint(lat + 0.000009, lon + 0.00009, 5),
        # Waypoint(lat - 0.000009, lon - 0.00009, 5),
        # Waypoint(lat + 0.000009, lon - 0.00009, 5),
        # Waypoint(lat, lon, alt + 10),  # Return to home
    ]
    connection.upload_mission(mission_coords)

    connection.start_mission()

# Main mission loop
    while not connection.monitor_mission_progress(stabilize_after_reached):
        process_single_frame(current_pos)
        time.sleep(FRAME_DELAY)


except KeyboardInterrupt:
    connection.log("⚠️ Mission interrupted by user")
except Exception as e:
    connection.log(f"❌ Mission failed: {traceback.print_exc()}")
finally:
    dataset_writer_context.__exit__(None, None, None)
    connection.log(
        "📊 Dataset collection completed: multi_stabilization_test.csv"
    )

    if camera and camera.cap.isOpened():
        camera.cap.release()
        cv2.destroyAllWindows()
        connection.log("📷 Camera stream closed")

    connection.clear_mission()
    connection.return_to_launch()
    connection.close()
    connection.log("✅ Mission cleanup complete")
