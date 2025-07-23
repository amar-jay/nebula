import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
import time

import cv2
import detection.yolo as yolo
import numpy as np

import src.controls.mavlink.gz as gz

logging.getLogger("ultralytics").setLevel(logging.WARNING)

# print(cv2.getBuildInformation())

pipeline = (
    "udpsrc port=5600 ! "
    "application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! "
    "rtph264depay ! "
    "h264parse ! "
    "avdec_h264 ! "
    "videoconvert ! "
    "appsink drop=1"
)

# done = gz.point_gimbal_downward(
#     topic="/gimbal/cmd_tilt",
#     angle=1.57)
# if not done:
#     print("❌ Failed to point gimbal downward.")
#     exit(1)

done = gz.enable_streaming(
    world="delivery_runway",
    model_name="iris_with_stationary_gimbal",
    camera_link="tilt_link",
)
if not done:
    print("❌ Failed to enable streaming.")
    exit(1)


cap = cv2.VideoCapture(pipeline)

height, width = 640, 640
# width, height, _ = camera.get_frame_size()
# cap = camera.get_capture()

estimator = yolo.YoloObjectTracker(
    model_path="src/controls/detection/sim.pt",
    K=np.ones((3, 3)),
)

print(f"[CAMERA]  → width: {width}, height: {height}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame. Is the stream active?")
        break

    results = estimator.detect(frame)
    # coords, center_pose, annotated_frame = estimator.process_frame(
    #     results, 0, 0, 10, object_class="helipad"
    # )
    # print(f"[YOLO]  →   detected {len(results)} objects.")
    # if coords is None or center_pose is None:
    #     cv2.putText(
    #         annotated_frame,
    #         "No target detected",
    #         (10, 30),
    #         cv2.FONT_HERSHEY_COMPLEX_SMALL,
    #         0.7,
    #         (0, 0, 255),
    #         2,
    #         cv2.LINE_AA,
    #     )
    #     cv2.imshow("Stream", frame)
    #     cv2.imshow("Annotated Stream", annotated_frame)
    #     continue

    # target_lat, target_lon = coords
    # cx, cy = center_pose
    # text_latlon = f"helipad Lat: {target_lat:.6f}, Lon: {target_lon:.6f}"
    # text_center = f"helipad Center: ({cx:.3f}, {cy:.3f})"

    # cv2.putText(
    #     annotated_frame,
    #     text_center,
    #     (10, 30),
    #     cv2.FONT_HERSHEY_COMPLEX_SMALL,
    #     0.7,
    #     (0, 0, 0),
    #     2,
    #     cv2.LINE_AA,
    # )
    # cv2.putText(
    #     annotated_frame,
    #     text_latlon,
    #     (10, 60),
    #     cv2.FONT_HERSHEY_COMPLEX_SMALL,
    #     0.7,
    #     (0, 0, 0),
    #     2,
    #     cv2.LINE_AA,
    # )

    cv2.imshow("Stream", frame)
    # cv2.imshow("Annotated Stream", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

    time.sleep(0.3)
cap.release()
# cv2.destroyAllWindows()
