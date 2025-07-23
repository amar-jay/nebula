import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional, Tuple, Union

import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DroneState:
    """Represents the current state of the drone."""

    latitude: float  # degrees
    longitude: float  # degrees
    altitude: float  # meters above sea level
    roll: float  # radians
    pitch: float  # radians
    yaw: float  # radians (heading)


@dataclass
class Detection:
    """Represents a single object detection."""

    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int
    class_name: str


@dataclass
class TrackedObject:
    """Represents a tracked object with history."""

    track_id: int
    bbox: Tuple[int, int, int, int]
    confidence: float
    class_name: str
    center: Tuple[float, float]
    history: List[Tuple[float, float]]  # Center points history


@dataclass
class GeolocationResult:
    """Result of geolocation estimation."""

    latitude: float
    longitude: float
    accuracy_meters: float
    confidence: float


class YOLODetector:
    """YOLO object detector wrapper."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.8):
        """
        Initialize YOLO detector.

        Args:
            model_path: Path to YOLO model file
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.class_names = ["helipad", "tank"]  # Expected classes

        # Load YOLO model (using OpenCV DNN as fallback)
        try:
            # Try to load with ultralytics if available
            from ultralytics import YOLO

            self.model = YOLO(model_path, verbose=False)
            self.use_ultralytics = True
            logger.info("Loaded YOLO model with ultralytics")
        except ImportError:
            # Fallback to OpenCV DNN
            self.net = cv2.dnn.readNet(model_path)
            self.use_ultralytics = False
            logger.info("Loaded YOLO model with OpenCV DNN")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in frame.

        Args:
            frame: Input image frame

        Returns:
            List of Detection objects
        """
        detections = []

        if self.use_ultralytics:
            results = self.model(frame, verbose=False)

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        conf = float(box.conf)
                        if conf >= self.confidence_threshold:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            class_id = int(box.cls)
                            class_name = (
                                self.class_names[class_id]
                                if class_id < len(self.class_names)
                                else f"class_{class_id}"
                            )

                            # Only process helipad and tank classes
                            if class_name in ["helipad", "tank"]:
                                detections.append(
                                    Detection(
                                        bbox=(x1, y1, x2, y2),
                                        confidence=conf,
                                        class_id=class_id,
                                        class_name=class_name,
                                    )
                                )
        else:
            # OpenCV DNN implementation
            height, width = frame.shape[:2]

            # Prepare input blob
            blob = cv2.dnn.blobFromImage(
                frame, 1 / 255.0, (640, 640), swapRB=True, crop=False
            )
            self.net.setInput(blob)

            # Forward pass
            outputs = self.net.forward()

            # Process outputs (simplified - assumes YOLOv5/v8 format)
            for output in outputs:
                for detection in output:
                    confidence = detection[4]
                    if confidence >= self.confidence_threshold:
                        class_scores = detection[5:]
                        class_id = np.argmax(class_scores)
                        class_confidence = class_scores[class_id]

                        if class_confidence >= self.confidence_threshold:
                            # Convert to pixel coordinates
                            center_x = int(detection[0] * width)
                            center_y = int(detection[1] * height)
                            w = int(detection[2] * width)
                            h = int(detection[3] * height)

                            x1 = int(center_x - w / 2)
                            y1 = int(center_y - h / 2)
                            x2 = int(center_x + w / 2)
                            y2 = int(center_y + h / 2)

                            class_name = (
                                self.class_names[class_id]
                                if class_id < len(self.class_names)
                                else f"class_{class_id}"
                            )

                            if class_name in ["helipad", "tank"]:
                                detections.append(
                                    Detection(
                                        bbox=(x1, y1, x2, y2),
                                        confidence=float(class_confidence),
                                        class_id=class_id,
                                        class_name=class_name,
                                    )
                                )

        return detections


class ObjectTracker(ABC):
    """Abstract base class for object trackers."""

    @abstractmethod
    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        """Update tracker with new detections."""
        pass


class SORTTracker(ObjectTracker):
    """SORT tracker implementation."""

    def __init__(self, max_age: int = 30, min_hits: int = 3):
        """
        Initialize SORT tracker.

        Args:
            max_age: Maximum frames to keep track without detection
            min_hits: Minimum hits before track is considered valid
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks = {}
        self.next_id = 1
        self.frame_count = 0

        # Try to import SORT from trackers library
        try:
            from trackers import SORT, SORTTracker

            self.sort = SORTTracker()
            # self.sort = SORT(max_age=max_age, min_hits=min_hits)
            self.use_library = True
            logger.info("Using SORT from trackers library")
        except ImportError:
            self.use_library = False
            logger.info("Using simplified SORT implementation")

    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        """Update tracker with new detections."""
        self.frame_count += 1
        tracked_objects = []

        if self.use_library:
            # Convert detections to format expected by SORT
            det_array = np.array(
                [
                    [d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3], d.confidence]
                    for d in detections
                ]
            )

            if len(det_array) == 0:
                det_array = np.empty((0, 5))

            # Update tracker
            tracks = self.sort.update(det_array)

            # Convert back to TrackedObject format
            for track in tracks:
                x1, y1, x2, y2, track_id = track
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                # Find corresponding detection for confidence and class
                best_det = None
                best_iou = 0
                for det in detections:
                    iou = self._calculate_iou((x1, y1, x2, y2), det.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_det = det

                if best_det:
                    tracked_obj = TrackedObject(
                        track_id=int(track_id),
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=best_det.confidence,
                        class_name=best_det.class_name,
                        center=(center_x, center_y),
                        history=[],
                    )
                    tracked_objects.append(tracked_obj)
        else:
            # Simplified tracking implementation
            tracked_objects = self._simple_tracking(detections)

        return tracked_objects

    def _simple_tracking(self, detections: List[Detection]) -> List[TrackedObject]:
        """Simplified tracking implementation."""
        tracked_objects = []

        for detection in detections:
            center_x = (detection.bbox[0] + detection.bbox[2]) / 2
            center_y = (detection.bbox[1] + detection.bbox[3]) / 2

            # Find closest existing track
            best_track_id = None
            best_distance = float("inf")

            for track_id, track_data in self.tracks.items():
                if track_data["class_name"] == detection.class_name:
                    last_center = track_data["last_center"]
                    distance = np.sqrt(
                        (center_x - last_center[0]) ** 2
                        + (center_y - last_center[1]) ** 2
                    )
                    if (
                        distance < best_distance and distance < 100
                    ):  # Max distance threshold
                        best_distance = distance
                        best_track_id = track_id

            if best_track_id is None:
                # Create new track
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = {
                    "class_name": detection.class_name,
                    "last_center": (center_x, center_y),
                    "history": [(center_x, center_y)],
                    "age": 0,
                    "hits": 1,
                }
            else:
                # Update existing track
                self.tracks[best_track_id]["last_center"] = (center_x, center_y)
                self.tracks[best_track_id]["history"].append((center_x, center_y))
                self.tracks[best_track_id]["age"] = 0
                self.tracks[best_track_id]["hits"] += 1
                track_id = best_track_id

            # Create tracked object
            tracked_obj = TrackedObject(
                track_id=track_id,
                bbox=detection.bbox,
                confidence=detection.confidence,
                class_name=detection.class_name,
                center=(center_x, center_y),
                history=self.tracks[track_id]["history"][-10:],  # Keep last 10 points
            )
            tracked_objects.append(tracked_obj)

        # Age tracks and remove old ones
        to_remove = []
        for track_id, track_data in self.tracks.items():
            track_data["age"] += 1
            if track_data["age"] > self.max_age:
                to_remove.append(track_id)

        for track_id in to_remove:
            del self.tracks[track_id]

        return tracked_objects

    def _calculate_iou(
        self,
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float],
    ) -> float:
        """Calculate Intersection over Union of two bounding boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0


class GeolocationEstimator:
    """Estimates world coordinates from image coordinates and drone state."""

    def __init__(self, camera_matrix: np.ndarray):
        """
        Initialize geolocation estimator.

        Args:
            camera_matrix: 3x3 camera intrinsic matrix
        """
        self.camera_matrix = camera_matrix
        self.earth_radius = 6378137.0  # Earth radius in meters (WGS84)

    def estimate_position(
        self, image_point: Tuple[float, float], drone_state: DroneState
    ) -> GeolocationResult:
        """
        Estimate world coordinates from image point and drone state.

        Args:
            image_point: (x, y) coordinates in image
            drone_state: Current drone state

        Returns:
            GeolocationResult with estimated coordinates and accuracy
        """
        # Convert image coordinates to normalized camera coordinates
        fx, fy = self.camera_matrix[0, 0], self.camera_matrix[1, 1]
        cx, cy = self.camera_matrix[0, 2], self.camera_matrix[1, 2]

        # Normalize image coordinates
        x_norm = (image_point[0] - cx) / fx
        y_norm = (image_point[1] - cy) / fy

        # Create ray in camera coordinate system
        ray_camera = np.array([x_norm, y_norm, 1.0])
        ray_camera = ray_camera / np.linalg.norm(ray_camera)

        # Transform ray to world coordinates using drone attitude
        R = self._rotation_matrix_from_euler(
            drone_state.roll, drone_state.pitch, drone_state.yaw
        )
        ray_world = R @ ray_camera

        # Calculate intersection with ground plane (assuming flat ground)
        # Ground plane is at altitude 0 (sea level)
        height_above_ground = drone_state.altitude

        # Calculate scale factor to reach ground
        if abs(ray_world[2]) < 1e-6:  # Ray is parallel to ground
            # Return drone position with low accuracy
            return GeolocationResult(
                latitude=drone_state.latitude,
                longitude=drone_state.longitude,
                accuracy_meters=1000.0,  # Very low accuracy
                confidence=0.1,
            )

        scale = -height_above_ground / ray_world[2]

        # Calculate ground intersection point in local coordinates
        ground_point_local = scale * ray_world

        # Convert local coordinates to GPS coordinates
        lat_offset = ground_point_local[1] / self.earth_radius * 180.0 / math.pi
        lon_offset = (
            ground_point_local[0]
            / (self.earth_radius * math.cos(math.radians(drone_state.latitude)))
            * 180.0
            / math.pi
        )

        target_lat = drone_state.latitude + lat_offset
        target_lon = drone_state.longitude + lon_offset

        # Estimate accuracy based on various factors
        accuracy = self._estimate_accuracy(drone_state, ray_world, height_above_ground)
        confidence = self._calculate_confidence(accuracy, height_above_ground)

        return GeolocationResult(
            latitude=target_lat,
            longitude=target_lon,
            accuracy_meters=accuracy,
            confidence=confidence,
        )

    def _rotation_matrix_from_euler(
        self, roll: float, pitch: float, yaw: float
    ) -> np.ndarray:
        """Create rotation matrix from Euler angles (roll, pitch, yaw)."""
        # Rotation matrices for each axis
        R_x = np.array(
            [
                [1, 0, 0],
                [0, math.cos(roll), -math.sin(roll)],
                [0, math.sin(roll), math.cos(roll)],
            ]
        )

        R_y = np.array(
            [
                [math.cos(pitch), 0, math.sin(pitch)],
                [0, 1, 0],
                [-math.sin(pitch), 0, math.cos(pitch)],
            ]
        )

        R_z = np.array(
            [
                [math.cos(yaw), -math.sin(yaw), 0],
                [math.sin(yaw), math.cos(yaw), 0],
                [0, 0, 1],
            ]
        )

        # Combined rotation matrix (ZYX convention)
        R = R_z @ R_y @ R_x
        return R

    def _estimate_accuracy(
        self, drone_state: DroneState, ray_world: np.ndarray, height: float
    ) -> float:
        """Estimate accuracy of geolocation in meters."""
        # Base accuracy factors
        base_accuracy = 1.0  # Base accuracy in meters

        # Height factor - higher altitude = less accuracy
        height_factor = height / 100.0  # 1 meter accuracy per 100m altitude

        # Angle factor - steeper angles = better accuracy
        angle_from_vertical = math.acos(abs(ray_world[2]))
        angle_factor = math.tan(angle_from_vertical) * 2.0

        # Camera resolution factor (simplified)
        resolution_factor = 0.5

        total_accuracy = (
            base_accuracy + height_factor + angle_factor + resolution_factor
        )

        return max(total_accuracy, 0.5)  # Minimum 0.5m accuracy

    def _calculate_confidence(self, accuracy: float, height: float) -> float:
        """Calculate confidence score (0-1) based on accuracy and conditions."""
        # Better accuracy = higher confidence
        accuracy_score = max(0.1, 1.0 - (accuracy / 20.0))

        # Reasonable height = higher confidence
        height_score = 1.0 if 10 <= height <= 200 else 0.5

        return min(accuracy_score * height_score, 1.0)


class HelipadTracker:
    """Main class for helipad detection, tracking, and geolocation."""

    def __init__(
        self,
        model_path: str,
        camera_matrix: np.ndarray,
        tracker_type: str = "sort",
        confidence_threshold: float = 0.8,
    ):
        """
        Initialize helipad tracker.

        Args:
            model_path: Path to YOLO model
            camera_matrix: 3x3 camera intrinsic matrix
            tracker_type: Type of tracker ('sort' or 'deepsort')
            confidence_threshold: Minimum confidence for detections
        """
        self.detector = YOLODetector(model_path, confidence_threshold)
        self.geolocation_estimator = GeolocationEstimator(camera_matrix)
        self.confidence_threshold = confidence_threshold

        # Initialize tracker
        if tracker_type.lower() == "sort":
            self.tracker = SORTTracker()
        else:
            # Could add DeepSORT here
            self.tracker = SORTTracker()
            logger.warning(f"Tracker type '{tracker_type}' not implemented, using SORT")

        # Store helipad positions
        self.helipad_positions = {}  # track_id -> GeolocationResult

    def process_frame(
        self, frame: np.ndarray, drone_state: DroneState
    ) -> Tuple[np.ndarray, Dict[int, GeolocationResult]]:
        """
        Process a single frame.

        Args:
            frame: Input video frame
            drone_state: Current drone state

        Returns:
            Tuple of (annotated_frame, helipad_positions_dict)
        """
        # Detect objects
        detections = self.detector.detect(frame)

        # Update tracker
        tracked_objects = self.tracker.update(detections)

        # Process helipads
        annotated_frame = frame.copy()
        current_helipads = {}

        for obj in tracked_objects:
            if obj.class_name == "helipad":
                # Estimate geolocation
                geolocation = self.geolocation_estimator.estimate_position(
                    obj.center, drone_state
                )

                # Store helipad position
                self.helipad_positions[obj.track_id] = geolocation
                current_helipads[obj.track_id] = geolocation

                # Annotate frame
                annotated_frame = self._annotate_frame(
                    annotated_frame, obj, geolocation
                )

        return annotated_frame, current_helipads

    def _annotate_frame(
        self,
        frame: np.ndarray,
        tracked_obj: TrackedObject,
        geolocation: GeolocationResult,
    ) -> np.ndarray:
        """Annotate frame with tracking and geolocation information."""
        x1, y1, x2, y2 = tracked_obj.bbox
        center_x, center_y = tracked_obj.center

        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw center point
        cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)

        # Draw track ID
        cv2.putText(
            frame,
            f"ID: {tracked_obj.track_id}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        # Draw GPS coordinates
        gps_text = f"GPS: {geolocation.latitude:.6f}, {geolocation.longitude:.6f}"
        cv2.putText(
            frame,
            gps_text,
            (x1, y2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        # Draw accuracy
        accuracy_text = (
            f"Acc: {geolocation.accuracy_meters:.1f}m ({geolocation.confidence:.2f})"
        )
        cv2.putText(
            frame,
            accuracy_text,
            (x1, y2 + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        return frame

    def process_video_stream(
        self,
        video_source: Union[str, int],
        drone_state_generator: Generator[DroneState, None, None],
    ) -> Generator[Tuple[np.ndarray, Dict[int, GeolocationResult]], None, None]:
        """
        Process video stream with drone state updates.

        Args:
            video_source: Video file path or camera index
            drone_state_generator: Generator yielding DroneState objects

        Yields:
            Tuples of (annotated_frame, helipad_positions)
        """
        cap = cv2.VideoCapture(video_source)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                try:
                    drone_state = next(drone_state_generator)
                except StopIteration:
                    break

                annotated_frame, helipad_positions = self.process_frame(
                    frame, drone_state
                )
                yield annotated_frame, helipad_positions

        finally:
            cap.release()


# Example usage function
def create_example_tracker():
    """Create an example tracker with dummy camera matrix."""
    # Example camera matrix (you should use your actual calibrated values)
    camera_matrix = np.array(
        [[800, 0, 320], [0, 800, 240], [0, 0, 1]]  # fx, 0, cx  # 0, fy, cy  # 0, 0, 1
    )

    # Initialize tracker
    tracker = HelipadTracker(
        model_path="best.pt",
        camera_matrix=camera_matrix,
        tracker_type="sort",
        confidence_threshold=0.8,
    )

    return tracker


# Example drone state generator
def example_drone_state_generator():
    """Example generator for drone states."""
    # This would typically come from your drone's telemetry system
    while True:
        yield DroneState(
            latitude=37.7749,  # San Francisco coordinates
            longitude=-122.4194,
            altitude=50.0,  # 50 meters above sea level
            roll=0.0,  # radians
            pitch=0.0,  # radians
            yaw=0.0,  # radians
        )


if __name__ == "__main__":
    # Example usage
    tracker = create_example_tracker()

    # Process a video file
    drone_states = example_drone_state_generator()

    for annotated_frame, helipad_positions in tracker.process_video_stream(
        "assets/input_video2.mp4", drone_states
    ):
        # Display results
        cv2.imshow("Helipad Tracking", annotated_frame)

        # Print helipad positions
        for track_id, position in helipad_positions.items():
            print(
                f"Helipad {track_id}: {position.latitude:.6f}, {position.longitude:.6f} "
                f"(±{position.accuracy_meters:.1f}m, conf: {position.confidence:.2f})"
            )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
