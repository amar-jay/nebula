import time

import cv2
from ultralytics import YOLO

# Load YOLOv8 model (change path/model type as needed)
model = YOLO("/home/amarjay/Downloads/Telegram Desktop/best.pt")

# Open video file
# video_path = "/home/amarjay/Desktop/drone-gimbal-raw.mp4"
# video_path = "rtsp://192.168.43.1:8554/fpv_stream"
video_path = "rtsp://rtspstream:63BXacyH9-6kVcLowNkb3@zephyr.rtsp.stream/people"
# video_path="rtsp://807e9439d5ca.entrypoint.cloud.wowza.com:1935/app-rC94792j/068b9c9a_stream2"
# cap = cv2.VideoCapture(video_path)

cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
# Set low-latency options if using FFMPEG
cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # try to keep only 3 frames in buffer to be safel


# pipeline = (
#     f"rtspsrc location={video_path} latency=0 ! "
#     "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink"
# )
# cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print(f"Error: Could not open video {video_path}")
    exit()

counter = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("End of video stream or cannot read frame.")
        break

    # Flush any old frames that accumulated
    # while cap.grab():          # grab discards old frames
    #     print("refreshing...")
    #     ret, frame = cap.retrieve()  # retrieve the most recent

    # Run inference
    if counter == 2:
        # time.sleep(0.1)
        now = time.time()
        results = model(frame)
        duration = time.time() - now
        print("Duration: ", duration)
        # Visualize results (bounding boxes / masks etc.)
        annotated_frame = results[0].plot()
        # Display in OpenCV window
        cv2.imshow("YOLOv8 Inference", annotated_frame)
        counter = 0

    counter += 1

    # Exit on 'q' key
    if cv2.waitKey(25) & 0xFF == ord("q"):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
