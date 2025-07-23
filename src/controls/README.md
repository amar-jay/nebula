# Drone Control and Object Detection

This repository contains code for controlling a drone using MAVLink, performing object detection using YOLO, and estimating GPS coordinates using an Extended Kalman Filter (EKF). The main functionality includes drone navigation, video streaming, object detection, and GPS estimation.

## Features

* Drone control using MAVLink
* Object detection using YOLO
* GPS estimation using an Extended Kalman Filter (EKF)
* Video streaming from Gazebo simulation
* Gamepad control for manual drone operation

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/amar-jay/controls.git
   cd controls
   ```

2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage

### Running the main script

The main script `__main__.py` controls the drone, performs object detection, and estimates GPS coordinates. To run the script, use the following command:
```sh
python __main__.py # or python .
```

### Calibrating the camera

Use amarjay's calibrate-camera repo

### Extracting frames from a video

To extract frames from a video, use the script `scripts/extract_frames_script.py`. This script extracts frames at a specified interval and saves them to a specified output folder.

### Testing the camera

To test the camera and object detection, use the script `scripts/camera_test.py`. This script captures video frames from the Gazebo simulation, performs object detection, and displays the annotated frames.

### Running the gamepad control script

To control the drone manually using a gamepad, use the script `scripts/gamepad_script.py`. This script reads input from a gamepad and sends manual control commands to the drone.

## Directory structure

* `detection/`: Contains YOLO object detection code and pre-trained model files.
  - `detection/yolo.py`: YOLO object detection and tracking.
  - `detection/cv.py`: Speed detection using ORB (not used).
  - `detection/best.pt`: Pre-trained YOLO model (skipped).

* `gps/`: Contains GPS-related code, including EKF and camera calibration.
  - `gps/ekf.py`: Extended Kalman Filter for GPS estimation.
  - `gps/calibrate_camera.py`: Camera calibration using checkerboard images.
  - `gps/angular.py`: Functions for computing angles and target GPS coordinates.

* `mavlink/`: Contains MAVLink-related code for drone control.
  - `mavlink/gz.py`: Functions for controlling the drone and enabling video streaming in Gazebo.
  - `mavlink/kamikaze.py`: Kamikaze drone mission script.

* `scripts/`: Contains utility scripts for various tasks.
  - `scripts/camera_test.py`: Script for testing the camera and object detection.
  - `scripts/extract_frames_script.py`: Script for extracting frames from a video.
  - `scripts/filter_test.py`: Script for testing the EKF.
  - `scripts/gamepad_script.py`: Script for controlling the drone using a gamepad.

* `__main__.py`: Main script for controlling the drone, performing object detection, and estimating GPS coordinates.
* `README.md`: This file.
* `requirements.txt`: List of required Python packages.
* `.gitignore`: Git ignore file.

