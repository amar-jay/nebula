# Drone Control and Object Detection

This section contains code for controlling a drone using MAVLink, performing object detection using YOLO, and estimating GPS coordinates using an Extended Kalman Filter (EKF). The main functionality includes drone navigation, video streaming server, object detection, and GPS estimation.

## Features

* Drone control using MAVLink
* Object detection using YOLO
* GPS estimation using an Extended Kalman Filter (EKF)
* Video streaming from Gazebo simulation


### Running the example script

The main script `__main__.py` controls the drone, performs object detection, and estimates GPS coordinates. To run the script, use the following command (You are free to toy around with the code it doesn't affect the major functionality in any way):
```sh
python . # or python __main__.py
```
Or also all other files prefixed by `_` can be run directly. such as `_test_tracker.py` etc.

### Camera calibration

To calibrate the camera, it is in two steps:
1. Capture images of a chessboard pattern using the camera. You can use the script `camera_calibration/capture_chessboard.py` to capture images and save them to a specified directory.
2. Use the captured images to compute the camera calibration parameters. You can use the script `camera_calibration/calibrate_camera.py` to perform the calibration and save the parameters to a file. using this update the `config/default.yaml` file with the path to the calibration parameters.

### Testing the camera

To test the camera and object detection, use the script `scripts/camera_test.py`. This script captures video frames from the Gazebo simulation, performs object detection, and displays the annotated frames. 