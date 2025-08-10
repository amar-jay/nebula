import time

import cv2

pipeline = (
    "udpsrc port=5600 ! "
    "application/x-rtp, encoding-name=H264 ! "
    "rtph264depay ! "
    "avdec_h264 ! "
    "videoconvert ! "
    "videorate ! "
    "video/x-raw,framerate=60/1 ! "
    "appsink"
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
# cap.set(cv2.CAP_PROP_FPS, 60)

if not cap.isOpened():
    print("Failed to open stream! Check sender or pipeline.")
    exit()

prev_time = time.time()
frame_count = 0
fps = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame.")
        break

    # FPS calculation
    frame_count += 1
    current_time = time.time()
    elapsed = current_time - prev_time
    if elapsed >= 1.0:
        fps = frame_count / elapsed
        prev_time = current_time
        frame_count = 0

    # Overlay FPS text
    cv2.putText(
        frame,
        f"FPS: {fps:.2f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    cv2.imshow("Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
