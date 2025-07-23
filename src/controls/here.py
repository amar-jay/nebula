import cv2
import numpy as np
import supervision as sv  # Requires `pip install supervision`
from trackers import SORTTracker  # Requires `pip install sort-tracker`
from ultralytics import YOLO  # Requires `pip install ultralytics`


# get current working directory
class YoloObjectTracker:
    def __init__(
        self,
        model_path="detection/best.pt",
        fov_deg=1,
        frame_width=640,
        frame_height=640,
    ):
        self.model = YOLO(model_path)
        self.tracker = SORTTracker()
        self.annotator = sv.LabelAnnotator(text_position=sv.Position.CENTER)
        self.fov_deg = fov_deg
        self.frame_width = frame_width
        self.frame_height = frame_height

    def detect(self, frame):
        results = self.model(frame, verbose=False)[
            0
        ]  # TODO: add some confidence threshold

        return results  # single frame

    def track(self, results):
        print(f"Results: {results.boxes[0]}")
        print("\n\n\n")
        detections = sv.Detections.from_ultralytics(results)
        detections = self.tracker.update(detections)
        print(f"Tracked {len(detections)} objects", detections[0])
        return detections

    def get_target_detection(self, detections, target_class):
        for box in detections.boxes:
            cls = int(box.cls[0])
            label = self.model.names[cls]
            if label == target_class:
                return box
        return None

    def get_object_center(self, box):
        x1, y1, x2, y2 = box.xyxy[0]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return float(cx), float(cy)

    def get_pixel_offset(self, cx, cy):
        dx = cx - self.frame_width / 2
        dy = cy - self.frame_height / 2
        return dx, dy

    def pixel_to_angle(self, dx, dy):
        """Convert pixel offset to angular offset."""
        fx = self.fov_deg / self.frame_width
        fy = self.fov_deg / self.frame_height
        return dx * fx, dy * fy

    def estimate_gps_offset(self, angle_dx, angle_dy, altitude):
        """Estimate how far the object is from the center in meters, assuming drone is fixed."""
        # Simple trig, assuming nadir (straight-down) view
        offset_x = np.tan(np.radians(angle_dx)) * altitude
        offset_y = np.tan(np.radians(angle_dy)) * altitude
        return offset_x, offset_y  # meters in X/Y plane

    def meters_to_gps(self, current_lat, current_lon, dx, dy):
        """Convert x/y offsets in meters to latitude and longitude offset."""
        # Approximate conversion assuming small angles and distance
        earth_radius = 6378137  # in meters

        dlat = dy / earth_radius
        dlon = dx / (earth_radius * np.cos(np.pi * current_lat / 180))

        new_lat = current_lat + (dlat * 180 / np.pi)
        new_lon = current_lon + (dlon * 180 / np.pi)

        return new_lat, new_lon

    def process_frame(
        self,
        detections,
        current_lat,
        current_lon,
        altitude,
        object_class="helipad",
        threshold=0.5,
    ):
        detections.boxes = detections.boxes[detections.boxes.conf > threshold]
        annotated_frame = detections.plot()
        target_box = self.get_target_detection(detections, object_class)
        if target_box is None:
            return None, None, annotated_frame

        cx, cy = self.get_object_center(target_box)
        dx, dy = self.get_pixel_offset(cx, cy)
        angle_dx, angle_dy = self.pixel_to_angle(dx, dy)
        offset_x, offset_y = self.estimate_gps_offset(angle_dx, angle_dy, altitude)
        target_gps = self.meters_to_gps(current_lat, current_lon, offset_x, offset_y)

        return target_gps, (cx, cy), annotated_frame


if __name__ == "__main__":
    import logging

    logging.getLogger("ultralytics").setLevel(logging.WARNING)

    input_video_path = "assets/input_video2.mp4"  # Path to your input video
    output_video_path = "assets/output.mp4"  # Path to your input video

    # Read the image using PIL and convert to numpy array
    # image_np = np.array(Image.open(random_test_image_path).convert("RGB"))
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"❌ Error opening video file: {input_video_path}")
        exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    out = cv2.VideoWriter(
        output_video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    # Load YOLO model
    estimator = YoloObjectTracker("detection/best.pt")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run inference
        results = estimator.detect(frame)
        try:
            w = estimator.process_frame(results, 0, 0, 10)
            (
                coords,
                center_pose,
                annotated_frame,
            ) = w  # TODO: add these parameters to frame -> return (target_lat, target_lon), (cx, cy), annotated_frame
            if coords is None or center_pose is None:
                cv2.putText(
                    annotated_frame,
                    "No target detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                out.write(annotated_frame)
                continue

            # Extract coordinates and center pose
            target_lat, target_lon = coords
            cx, cy = center_pose
            text_latlon = f"Lat: {target_lat:.6f}, Lon: {target_lon:.6f}"
            text_center = f"Center: ({cx}, {cy})"

            pos1 = (10, 30)
            pos2 = (10, 60)

            cv2.putText(
                annotated_frame,
                text_latlon,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                annotated_frame,
                text_center,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            out.write(annotated_frame)

        except ValueError as e:
            print(f"❌ {e}")
            # If no target detected, just write the original frame
            out.write(frame)

    cap.release()
    out.release()
    print(f"✅ Output saved to {output_video_path}")

    # Load the original image
    # image = cv2.imread(random_test_image_path)

    # res = results.plot()
    # cv2.imwrite("output.jpg", annotated_frame)

    # # Draw boxes and labels
    # for box in results.boxes:
    #     x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    #     conf = box.conf[0].item()
    #     cls = int(box.cls[0].item())
    #     label = estimator.model.names[cls]

    #     print(f"→ {label} with {conf:.2%} confidence")
    #     # Draw rectangle and label
    #     cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    #     cv2.putText(
    #         image,
    #         f"{label} {conf:.2f}",
    #         (x1, y1 - 10),
    #         cv2.FONT_HERSHEY_SIMPLEX,
    #         0.6,
    #         (0, 255, 0),
    #         2,
    #     )

    # # Save the annotated image
    # cv2.imwrite("output.jpg", image)
    # print(f"Annotated image saved to output.jpg")

    # # Create tracker and run detection
    # estimator = YoloObjectTracker("detection/best.pt")
    # result_frame = estimator.detect(image_np)  # detect expects numpy frame
    # print(f"{result_frame=}")

    # Save the resulting image using PIL (not OpenCV)
    # result_image = Image.fromarray(result_frame)
    # output_path = "./output_detected.jpg"
    # result_image.save(output_path, format="JPEG")
    # print(f"Saved output to {output_path}")
    # random_test_image = random.choice(os.listdir("./frames"))
    # print("running inference on " + random_test_image)
