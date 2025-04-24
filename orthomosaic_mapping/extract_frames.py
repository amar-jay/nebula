import cv2

video_path = "your_video.mp4"  # Replace with your actual path
cap = cv2.VideoCapture(video_path)

# Frame numbers you want to extract (e.g., frame 10 and frame 100)
frame_ids = [10, 100]
extracted = []

frame_idx = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if frame_idx in frame_ids:
        extracted.append(frame)
        print(f"Extracted frame {frame_idx}")
        if len(extracted) == len(frame_ids):
            break

    frame_idx += 1

cap.release()

# Save extracted frames as images
for i, img in enumerate(extracted):
    cv2.imwrite(f"frame_{frame_ids[i]}.jpg", img)

print("Done!")

