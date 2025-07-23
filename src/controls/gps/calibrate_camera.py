import glob

import cv2
import numpy as np

# Set up the checkerboard dimensions
# for this there are 8 squares in each row and there are 7 squares in each column. (black and white alternating)
checkerboard_dims = (7, 6)  # number of internal corners per checkerboard row and column

# Prepare object points (3D coordinates of the checkerboard corners in real world space)
obj_points = np.zeros((np.prod(checkerboard_dims), 3), np.float32)
obj_points[:, :2] = np.indices(checkerboard_dims).T.reshape(-1, 2)

# Arrays to store object points and image points from all images
obj_points_all = []
img_points_all = []

# Load calibration images
images = glob.glob("calibration_images/*.jpg")

# Process each image
for image_file in images:
    image = cv2.imread(image_file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Find the checkerboard corners
    ret, corners = cv2.findChessboardCorners(gray, checkerboard_dims, None)

    if ret:
        obj_points_all.append(obj_points)
        img_points_all.append(corners)

        # Draw and display the corners
        cv2.drawChessboardCorners(image, checkerboard_dims, corners, ret)
        cv2.imshow("Checkerboard", image)
        cv2.waitKey(500)

# Calibrate the camera
ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
    obj_points_all, img_points_all, gray.shape[::-1], None, None
)

# Print the camera matrix
print("Camera Matrix:")
print(camera_matrix)
np.save("camera_matrix.npy", camera_matrix)


# Extract the focal length from the camera matrix
focal_length = camera_matrix[
    0, 0
]  # Focal length (fx), since the matrix is typically (fx, 0, cx)
print(f"Focal Length (fx): {focal_length}")
