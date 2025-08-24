import cv2
from ultralytics import YOLO

# Load YOLOv8 model (change path/model type as needed)
model = YOLO("/home/amarjay/Downloads/Telegram Desktop/best.pt")

# Open video file
video_path = "/home/amarjay/Desktop/drone-gimbal-raw.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Could not open video {video_path}")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("End of video stream or cannot read frame.")
        break

    # Run inference
    results = model(frame)

    # Visualize results (bounding boxes / masks etc.)
    annotated_frame = results[0].plot()

    # Display in OpenCV window
    cv2.imshow("YOLOv8 Inference", annotated_frame)

    # Exit on 'q' key
    if cv2.waitKey(25) & 0xFF == ord("q"):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
