import time

import cv2

from src.controls.mavlink.gz import GazeboVideoCapture
from src.mq.video_writer import RTSPVideoWriter

# cap = GazeboVideoCapture("")
cap = cv2.VideoCapture("rtsp://localhost:8554/raw")
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))
print("FPS: ", fps)
print("Width: ", width)
print("Height: ", height)

start_time = time.time()
if not cap.isOpened():
    print("Failed to open stream")

else:
    video_writer = RTSPVideoWriter(
        source="rtsp://127.0.0.1:8554/processed",
        width=width,
        height=height,
        fps=fps,
    )

    if video_writer is None or not video_writer.isOpened():
        print("Failed to open video writer")
        exit(1)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
        cv2.imshow("RTP Stream", frame)
        video_writer.write(frame.copy())
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

cap.release()
cv2.destroyAllWindows()
