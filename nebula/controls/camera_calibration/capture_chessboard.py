import argparse
import os

import cv2


def capture_calibration_images(camera_id, chessboard_size, output_dir):
    """
    Capture images of a chessboard pattern for camera calibration.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_id}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {width}x{height}")

    img_counter = 0
    print("Press 'c' to capture an image")
    print("Press 'q' or Escape to quit")
    print(f"Images will be saved to {output_dir}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret_chess, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

        # NOTE: AWFULLY SLOW WITHOUT CUDA ACCELERATION, SO I ADVISE TO JUST TRUST YOURSELF TO CAPTURE GOOD IMAGES
        if ret_chess:
            cv2.drawChessboardCorners(frame, chessboard_size, corners, ret_chess)
            cv2.putText(
                frame,
                "Chessboard detected!",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        cv2.putText(
            frame,
            f"Captured: {img_counter}",
            (50, height - 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        cv2.imshow("Camera Calibration", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            print("Exiting...")
            break
        elif key == ord("c"):
            img_name = os.path.join(output_dir, f"calibration_{img_counter:02d}.jpg")
            cv2.imwrite(img_name, frame)
            print(f"Captured {img_name}")
            img_counter += 1

    cap.release()
    cv2.destroyAllWindows()
    print(f"Captured {img_counter} images for calibration")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture images of a chessboard for camera calibration."
    )
    parser.add_argument(
        "--camera_id", type=int, default=0, help="Camera device ID (default: 0)"
    )
    parser.add_argument(
        "--chessboard_rows",
        type=int,
        default=23,
        help="Number of inner corners per row",
    )
    parser.add_argument(
        "--chessboard_cols",
        type=int,
        default=15,
        help="Number of inner corners per column",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="calibration_images",
        help="Directory to save images",
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    chessboard_size = (args.chessboard_rows, args.chessboard_cols)
    capture_calibration_images(args.camera_id, chessboard_size, args.output_dir)
