# pylint: disable=E1101
import csv
import logging
from contextlib import contextmanager
from typing import Dict, List, NamedTuple, Optional, Tuple

import cv2
import numpy as np
import supervision as sv
from trackers import SORTTracker
from ultralytics import YOLO

# Constants
EARTH_RADIUS_M = 6378137.0


# Suppress ultralytics logging
logging.getLogger("ultralytics").setLevel(logging.WARNING)
logger = logging.getLogger("yolo_tracker")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Detection(NamedTuple):
    """Detection result with all relevant information"""

    center_pixel: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    confidence: float
    class_id: int
    size: Tuple[float, float]
    track_id: Optional[int] = None


class YoloObjectTracker:
    """Enhanced YOLO object tracker with GPS estimation capabilities"""

    def __init__(
        self,
        K: np.ndarray,
        model_path: str = "detection/best.pt",
    ):
        self.model = YOLO(model_path, verbose=False)
        self.names = list(dict(self.model.names).values())
        logger.info(f"Model classes: {', '.join(self.names)}")

        self.annotator = sv.LabelAnnotator(text_position=sv.Position.CENTER)
        self.tracker = SORTTracker()

        self.K = K

    def _validate_object_classes(self, object_classes: List[str]) -> None:
        """Validate that all requested object classes exist in the model"""
        model_classes = set(self.names)
        for object_class in object_classes:
            if object_class not in model_classes:
                raise ValueError(
                    f"Object class '{object_class}' not found in model classes: "
                    f"{', '.join(self.names)}"
                )

    def _detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
        object_classes: Tuple[str, str] = ("helipad", "real_tank"),
    ) -> Dict[str, Detection]:
        """
        Detect objects in image and return structured detection results

        Args:
            image: Input image
            confidence_threshold: Minimum confidence for detections
            object_classes: List of object classes to detect

        Returns:
            Dictionary mapping object class names to Detection objects
        """
        self._validate_object_classes(object_classes)

        results = self.model(image, conf=confidence_threshold)
        if len(results) == 0:
            return {}

        detections = sv.Detections.from_ultralytics(results[0])
        tracked_detections = self.tracker.update(detections)

        outputs = {}
        boxes = results[0].boxes

        if boxes is not None:
            for i, box in enumerate(boxes):
                class_name = self.model.names[int(box.cls[0])]

                if class_name in object_classes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    width = x2 - x1
                    height = y2 - y1

                    # Get track ID if available
                    track_id = None
                    if (
                        hasattr(tracked_detections, "tracker_id")
                        and tracked_detections.tracker_id is not None
                        and len(tracked_detections.tracker_id) > i
                    ):
                        track_id = tracked_detections.tracker_id[i]

                    detection = Detection(
                        center_pixel=(center_x, center_y),
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=confidence,
                        class_id=class_id,
                        size=(width, height),
                        track_id=track_id,
                    )

                    # Store the best detection for each class
                    if (
                        class_name not in outputs
                        or detection.confidence > outputs[class_name].confidence
                    ):
                        outputs[class_name] = detection

        return outputs

    def _create_rotation_matrix(
        self, roll: float, pitch: float, yaw: float
    ) -> np.ndarray:
        """Create rotation matrix from Euler angles"""
        R_x = np.array(
            [
                [1, 0, 0],
                [0, np.cos(roll), -np.sin(roll)],
                [0, np.sin(roll), np.cos(roll)],
            ]
        )
        R_y = np.array(
            [
                [np.cos(pitch), 0, np.sin(pitch)],
                [0, 1, 0],
                [-np.sin(pitch), 0, np.cos(pitch)],
            ]
        )
        R_z = np.array(
            [
                [np.cos(yaw), -np.sin(yaw), 0],
                [np.sin(yaw), np.cos(yaw), 0],
                [0, 0, 1],
            ]
        )
        return R_z @ R_y @ R_x

    def _offset_gps(
        self, lat: float, lon: float, north: float, east: float
    ) -> Tuple[float, float]:
        """Convert North-East offsets to GPS coordinates"""
        dLat = north / EARTH_RADIUS_M
        dLon = east / (EARTH_RADIUS_M * np.cos(np.deg2rad(lat)))
        return lat + np.rad2deg(dLat), lon + np.rad2deg(dLon)

    def _pixel_to_gps(
        self,
        pixel_coords: Tuple[int, int],
        drone_gps: Tuple[float, float, float],
        drone_attitude: Tuple[float, float, float],
        K: Optional[np.ndarray] = None,
    ) -> Optional[Tuple[float, float]]:
        """
        Convert pixel coordinates to GPS coordinates

        Args:
            pixel_coords: (u, v) pixel coordinates
            drone_gps: (lat, lon, alt_masl) drone GPS position
            drone_attitude: (roll, pitch, yaw) in degrees
            ground_level_masl: Ground elevation in meters above sea level
            K: Camera intrinsic matrix (uses default if None)

        Returns:
            (lat, lon) GPS coordinates or None if computation fails
        """
        if K is None:
            K = self.K

        drone_lat, drone_lon, drone_alt_masl = drone_gps
        roll, pitch, _yaw = drone_attitude
        """
        NOTE on Yaw Handling:
        !!!!!!!!!!!!!!!!DO NOT TOUCH!!!!!!!!!!!!!!

        In MAVLink/NED convention, the drone's yaw angle may be reported
        with a sign opposite to the mathematical convention used in the
        camera rotation calculation. As a result, when converting pixel
        coordinates to GPS coordinates, the yaw must be negated to align
        the camera's orientation with the NED frame.

        This fixes the issue where the computed target GPS point is
        significantly offset even for nadir-facing cameras.
        """
        roll, pitch, yaw = np.deg2rad([roll, pitch, -_yaw])

        # Height above ground
        height_above_ground = drone_alt_masl #- ground_level_masl
        if height_above_ground <= 0:
            logger.warning("Drone is at or below ground level — cannot compute GPS")
            return None

        # Convert pixel to camera ray
        u, v = pixel_coords
        pixel_homog = np.array([u, v, 1.0])

        try:
            K_inv = np.linalg.inv(K)
        except np.linalg.LinAlgError:
            logger.error("Camera intrinsic matrix is singular")
            return None

        cam_ray = K_inv @ pixel_homog
        cam_ray = cam_ray / np.linalg.norm(cam_ray)

        # Transform to world coordinates
        R = self._create_rotation_matrix(roll, pitch, yaw)
        dir_world = R @ cam_ray

        # Check if ray points downward
        if dir_world[2] >= 0:
            logger.warning(
                f"Camera ray points upward/horizontal (z={dir_world[2]:.3f})"
            )
            # return None

        # Compute intersection with ground plane
        t = height_above_ground / -dir_world[2]
        offset_ned = t * dir_world

        # Convert to GPS
        target_lat, target_lon = self._offset_gps(
            drone_lat, drone_lon, offset_ned[0], offset_ned[1]
        )

        return target_lat, target_lon

    def _calculate_gps_error(
        self, pred_lat: float, pred_lon: float, gt_lat: float, gt_lon: float
    ) -> float:
        """Haversine distance calculation using numpy"""
        phi1 = np.deg2rad(gt_lat)
        phi2 = np.deg2rad(pred_lat)
        dphi = np.deg2rad(pred_lat - gt_lat)
        dlambda = np.deg2rad(pred_lon - gt_lon)

        a = (
            np.sin(dphi / 2) ** 2
            + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
        )
        return float(2 * EARTH_RADIUS_M * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

    def write_on_frame(
        self,
        frame: np.ndarray,
        curr_gps: Tuple[
            float, float, float
        ],  # current GPS of the drone (lat, lon, alt)
        gps_coords: Dict[str, Tuple[float, float]],
        pixel_coords: Dict[str, Tuple[int, int]],
        mode="UNKNOWN",
        object_classes: Tuple[str, str] = ("helipad", "real_tank"),
        fps=30.0,
    ):
        """Write overlay information on the frame"""
        _, frame_w = frame.shape[:2]
        overlay = frame.copy()

        # Elegant blue-toned mode colors
        mode_colors = {
            "GUIDED": (255, 180, 90),
            "STABILIZE": (150, 150, 255),
            "AUTO": (100, 180, 255),
            "LOITER": (180, 100, 255),
        }
        default_color = (200, 200, 255)
        mode_color = mode_colors.get(mode.upper(), default_color)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 1

        # Draw object labels
        for obj in object_classes:
            if obj in pixel_coords:
                px, py = pixel_coords[obj]
                lat, lon = gps_coords.get(obj, (None, None))

                text_color = (255, 255, 255)
                accent_color = (255, 160, 130)

                cv2.circle(overlay, (px, py), 6, accent_color, -1)

                label = f"{obj.upper()}"
                if lat is not None and lon is not None:
                    label += f" | ({lat:.6f}, {lon:.6f})"

                (label_w, label_h), _ = cv2.getTextSize(label, font, 0.5, 1)
                rect_tl = (px + 10, py - label_h - 10)
                rect_br = (px + 16 + label_w, py)
                cv2.rectangle(overlay, rect_tl, rect_br, accent_color, -1)
                cv2.putText(
                    overlay,
                    label,
                    (px + 13, py - 5),
                    font,
                    0.5,
                    text_color,
                    1,
                    cv2.LINE_AA,
                )

        # Draw mode info (top-right)
        mode_text = f"MODE: {mode.upper()}"
        (text_w, text_h), _ = cv2.getTextSize(
            mode_text, font, font_scale, font_thickness
        )
        padding = 12
        x = frame_w - text_w - padding
        y = text_h + padding

        mode_overlay = overlay.copy()
        cv2.rectangle(
            mode_overlay,
            (x - 8, y - text_h - 6),
            (x + text_w + 8, y + 6),
            (30, 30, 50),
            -1,
        )
        cv2.addWeighted(mode_overlay, 0.6, overlay, 0.4, 0, overlay)
        cv2.putText(
            overlay,
            mode_text,
            (x, y),
            font,
            font_scale,
            mode_color,
            font_thickness + 1,
            cv2.LINE_AA,
        )

        fps_text = f"FPS: {fps:.2f}"
        cv2.putText(
            overlay,
            fps_text,
            (10, y),  # Position (x, y)
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (100, 100, 0),
            2,
        )

        # Draw current GPS and distance to helipad (bottom-left)
        gps_text_lines = []
        curr_lat, curr_lon, curr_alt = curr_gps
        gps_text_lines.append(f"GPS: ({curr_lat:.6f}, {curr_lon:.6f}, {curr_alt:.1f}m)")

        if "helipad" in gps_coords:
            helipad_latlon = gps_coords["helipad"]
            dist = self._calculate_gps_error(
                curr_lat, curr_lon, helipad_latlon[0], helipad_latlon[1]
            )
            gps_text_lines.append(f"D: {dist:.1f} m")

        start_x, start_y = 12, frame.shape[0] - 12
        for i, line in enumerate(reversed(gps_text_lines)):
            (tw, th), _ = cv2.getTextSize(line, font, font_scale, font_thickness)
            rect_tl = (start_x - 6, start_y - th - 6 - i * int(1.5 * th))
            rect_br = (start_x + tw + 6, start_y + 4 - i * int(1.5 * th))

            cv2.rectangle(overlay, rect_tl, rect_br, (50, 30, 30), -1)
            cv2.putText(
                overlay,
                line,
                (start_x, start_y - i * int(1.5 * th)),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness,
                cv2.LINE_AA,
            )

        # Blend overlay with original
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        return frame

    def write_on_frame_old(
        self,
        frame: np.ndarray,
        gps_coords: Dict[str, Tuple[float, float]],
        pixel_coords: Dict[str, Tuple[int, int]],
        mode="UNKNOWN",
        object_classes: Tuple[str, str] = ("helipad", "real_tank"),
    ):
        _, frame_w = frame.shape[:2]
        overlay = frame.copy()

        # Define colors
        mode_colors = {
            "GUIDED": (0, 255, 0),  # Green
            "STABILIZE": (0, 255, 255),  # Yellow
        }
        default_color = (100, 100, 255)  # Light Red
        mode_color = mode_colors.get(mode.upper(), default_color)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2

        # Draw object labels
        for obj in object_classes:
            if obj in pixel_coords:
                px, py = pixel_coords[obj]
                lat, lon = gps_coords.get(obj, (None, None))

                color = (255, 255, 255)
                box_color = (255, 120, 80)  # Beautiful blue variant

                # Draw a circle on the object
                cv2.circle(overlay, (px, py), 8, box_color, -1)

                # Draw a label box
                label = f"{obj.upper()}"
                if lat is not None and lon is not None:
                    label += f" | ({lat:.6f}, {lon:.6f})"

                (label_w, label_h), _ = cv2.getTextSize(label, font, 0.5, 1)
                label_rect_top_left = (px + 10, py - label_h - 10)
                label_rect_bottom_right = (px + 10 + label_w + 6, py)
                cv2.rectangle(
                    overlay, label_rect_top_left, label_rect_bottom_right, box_color, -1
                )
                cv2.putText(
                    overlay, label, (px + 13, py - 5), font, 0.5, color, 1, cv2.LINE_AA
                )

        # Draw mode in top-right
        mode_text = f"MODE: {mode.upper()}"
        (text_w, text_h), _ = cv2.getTextSize(
            mode_text, font, font_scale, font_thickness
        )
        padding = 10
        x = frame_w - text_w - padding
        y = text_h + padding

        # Create translucent black background
        mode_overlay = overlay.copy()
        cv2.rectangle(
            mode_overlay,
            (x - 5, y - text_h - 5),
            (x + text_w + 5, y + 5),
            (0, 0, 0),
            -1,
        )
        cv2.addWeighted(mode_overlay, 0.7, overlay, 0.3, 0, overlay)

        # Draw text with mode color
        cv2.putText(
            overlay,
            mode_text,
            (x, y),
            font,
            font_scale,
            mode_color,
            font_thickness,
            cv2.LINE_AA,
        )

        # Apply the overlay with transparency
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        return frame

    def process_frame(
        self,
        frame: np.ndarray,
        drone_gps: Tuple[float, float, float],
        drone_attitude: Tuple[float, float, float],
        # ground_level_masl: float,
        K: Optional[np.ndarray] = None,
        object_classes: Tuple[str, str] = ("helipad", "real_tank"),
        threshold: float = 0.5,
    ) -> Tuple[np.ndarray, Dict[str, Tuple[float, float]], Dict[str, Tuple[int, int]]]:
        """
        Process a single frame for object detection and GPS estimation

        Returns:
            Tuple of (annotated_frame, gps_coordinates, pixel_coordinates)
        """
        detections = self._detect(
            frame, confidence_threshold=threshold, object_classes=object_classes
        )

        if not detections:
            # self.log("No objects detected")
            return frame, {}, {}

        # self.log(f"Detected {len(detections)} objects")

        gps_coords: dict[str, Tuple[float, float]] = {}
        pixel_coords: dict[str, Tuple[int, int]] = {}

        for object_class, detection in detections.items():
            # Draw bounding box and center
            x1, y1, x2, y2 = detection.bbox
            center = detection.center_pixel

            color = (100, 255, 0)  # Could be made configurable
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # cv2.circle(frame, center, 8, (255, 0, 255), -1)

            # Add label with tracking ID if available
            label = f"{object_class}: {detection.confidence:.2f}"
            if detection.track_id is not None:
                label += f" (ID: {detection.track_id})"

            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

            # Compute GPS coordinates
            gps_result = self._pixel_to_gps(
                pixel_coords=center,
                drone_gps=drone_gps,
                drone_attitude=drone_attitude,
                K=K,
            )

            if gps_result is not None:
                gps_coords[object_class] = gps_result
                pixel_coords[object_class] = center

        return frame, gps_coords, pixel_coords

    @contextmanager
    def dataset_writer(self, dataset_path: str):
        """Context manager for writing dataset CSV files"""
        try:
            with open(dataset_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if f.tell() == 0:  # Write header if file is empty
                    writer.writerow(
                        ["pixel", "gps_true", "drone_gps", "drone_attitude"]
                    )
                yield writer
        except Exception as e:
            logger.error(f"Error writing dataset: {e}")
            raise


def main():
    """Example usage of the improved tracker"""

    input_video_path = "/home/amarjay/Desktop/long.MOV"
    output_video_path = "/home/amarjay/Desktop/long-processed.MOV"

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        logger.error(f"Error opening video file: {input_video_path}")
        return

    # Video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Output video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    # Camera intrinsics (adjust for your camera)
    K = np.array([[959.41, 0.0, 626.26], [0.0, 960.10, 357.03], [0.0, 0.0, 1.0]])

    # Initialize tracker
    estimator = YoloObjectTracker(
        K=K,
        model_path="/home/amarjay/Desktop/code/matek/src/controls/detection/best_v2.pt",
    )

    # Configuration
    object_classes = ("helipad", "real_tank")
    object_colors = {
        "helipad": (0, 255, 0),
        "real_tank": (255, 100, 100),
    }

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            try:
                annotated_frame, gps_dict, pixel_dict = estimator.process_frame(
                    frame,
                    drone_gps=(0, 0, 410),  # Replace with actual GPS
                    drone_attitude=(0, 0, 0),  # Replace with actual attitude
                    # ground_level_masl=387,
                    K=K,
                    object_classes=object_classes,
                    threshold=0.5,
                )

                # Add overlay information
                if not gps_dict:
                    cv2.putText(
                        annotated_frame,
                        "No target detected",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2,
                    )
                else:
                    # Create semi-transparent overlay
                    overlay = annotated_frame.copy()
                    cv2.rectangle(
                        overlay, (0, 0), (500, 30 + 40 * len(gps_dict)), (0, 0, 0), -1
                    )
                    cv2.addWeighted(
                        overlay, 0.7, annotated_frame, 0.3, 0, annotated_frame
                    )

                    y_offset = 30
                    for object_class, (lat, lon) in gps_dict.items():
                        center = pixel_dict.get(object_class)
                        color = object_colors.get(object_class, (200, 200, 0))

                        cv2.putText(
                            annotated_frame,
                            f"{object_class.upper()}: {lat:.6f}, {lon:.6f}",
                            (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            color,
                            2,
                        )
                        y_offset += 25

                        if center:
                            cv2.putText(
                                annotated_frame,
                                f"Pixel: ({center[0]}, {center[1]})",
                                (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                color,
                                2,
                            )
                            y_offset += 30

                out.write(annotated_frame)

            except Exception as e:
                logger.error(f"Error processing frame {frame_count}: {e}")
                out.write(frame)

    finally:
        cap.release()
        out.release()
        logger.info(f"Output saved to {output_video_path}")


if __name__ == "__main__":
    main()
