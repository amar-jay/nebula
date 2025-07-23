import os

import cv2


def center_crop_and_resize(image, size=640):
    h, w = image.shape[:2]

    # Step 1: Center crop to square
    if h > w:
        top = (h - w) // 2
        cropped = image[top : top + w, :]
    else:
        left = (w - h) // 2
        cropped = image[:, left : left + h]

    # Step 2: Resize to target size
    resized = cv2.resize(cropped, (size, size), interpolation=cv2.INTER_AREA)
    return resized


def extract_frames(video_path, output_folder, interval_ms):
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Input Video dimensions: {width} x {height}")

    # Get video FPS (frames per second)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Unable to get FPS from video.")
        return

    # Calculate interval in frames
    interval_frames = int((interval_ms / 1000) * fps)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(
        f"Video FPS: {fps}, Total frames: {total_frames}, Interval: {interval_frames} frames, Frames to save: {total_frames // interval_frames}"
    )

    # Make output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    frame_id = 0
    saved_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = center_crop_and_resize(frame)

        if frame_id % interval_frames == 0:
            filename = os.path.join(output_folder, f"frame_{frame_id:05d}.jpg")
            cv2.imwrite(filename, frame)
            saved_count += 1

        frame_id += 1

    cap.release()
    print(f"Saved {saved_count} frames to '{output_folder}'.")


if __name__ == "__main__":
    # Example usage
    video_file = "assets/input_video.mp4"
    output_dir = "assets/frames"

    os.makedirs(output_dir, exist_ok=True)
    extract_frames(video_file, output_dir, interval_ms=1000)  # Extract every 1 second
