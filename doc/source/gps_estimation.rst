GPS Estimation
==============

.. _gps:

One major part of the Nebula project is its GPS Estimation module. In our github its located under ``src/controls/detection`` directory.
It is responsible for estimating the GPS coordinates of a single pixel within a camera frame from a nadir (facing downward) mounted camera.
Now, the GPS Estimation module is designed to work with a monocular camera setup, meaning it uses a single camera to capture images and estimate GPS coordinates.
This is in contrast to stereo camera setups that use two cameras to capture depth information. We use a pinhole camera model for our camera setup.

Basically, our GPS Estimation module consists of two major parts. 
One is estimating the exact pixel location of the object of interest (helipad or tank) within the camera frame using our image recognition model.
The second part is estimating the GPS coordinates of that pixel using the camera's intrinsic and extrinsic parameters along with the drone's GPS coordinates and altitude provided by MAVLink.


Image Recognition
-----------------

Our Image Recognition model is a custom-trained YoloV8 model. It is trained to detect 4 classes of objects: helipad, tanks, sim_tank, and sim_helipad. That is two sets of real and simulated objects, that is the tank and helipad.

the sim_helipad is a subset of helipad tagged images that is only taken from the simulated environment. Similarly, sim_tank is a subset of tank tagged images taken from the simulated environment.

We trained our model on nearly a thousand images combined from real-world and simulated environments. The model is trained to detect these objects from a nadir (facing downward) mounted camera as well as from various oblique angles.

For image annotation, we used the `Roboflow <https://roboflow.com/>`_ platform. After annotating the images, we exported them in YOLO format and used Google Colab to train the model. It is a very straightforward process but time-consuming.


Camera Calibration
------------------

To be able to estimate GPS coordinates from pixel locations, we need to know the camera's intrinsic parameters. These parameters include focal length, principal point, and distortion coefficients.

Using the camera intrinsics, we can adopt the pinhole camera model to map 3D world coordinates to 2D image coordinates and from that we can reverse the process to map 2D image coordinates back to 3D world coordinates.

This is a standard computer vision technique. For calibration we use the OpenCV's chessboard calibration method. `Here is a good tutorial <https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html>`_ on how to do camera calibration using OpenCV.
Or you can use the one from our GitHub repo located at ``src/controls/detection/camera_calibration.py``. 

Some pinhole cameras introduce significant distortion to images. Two major kinds of distortion are radial distortion and tangential distortion.
However in our case, we are using a high-quality camera with a wide-angle lens that introduces minimal distortion. So we can safely ignore distortion coefficients in our calculations.
So we only need the focal length and principal point for our GPS estimation calculations. but its best to just get the **K matrix** from the calibration process, that has proven to be more accurate.

GPS Coordinate Estimation
-------------------------

Once we have the pixel coordinates of the object of interest from our image recognition model and the camera's intrinsic parameters from the calibration process, we can proceed to estimate the GPS coordinates.

The GPS estimation process involves several steps:

Once we have the pixel coordinates of the object of interest from our image recognition model and the camera's intrinsic parameters from the calibration process, we can proceed to estimate the GPS coordinates.

The GPS estimation process below is presented in a clear, sorted order followed by the key formulas used. We assume a nadir-mounted camera (optical axis approximately aligned with the down direction) and negligible lens distortion (distortion coefficients ignored or already compensated in preprocessing).

Steps
~~~~~

1. Get drone reference: obtain the drone's current GPS coordinates (latitude phi_0, longitude lambda_0) and altitude h above the ellipsoid (or above ground if available). For higher accuracy use RTK-corrected GPS instead of raw GNSS data.

2. Get camera pose: obtain the camera extrinsics relative to the drone body and the drone attitude (rotation/roll/pitch/yaw). From these we build the rotation R_cb (camera-to-body) and R_be (body-to-ENU/world) matrices. Combined camera-to-ENU rotation is R_ce = R_be * R_cb.

3. Convert pixel to normalized camera coordinates (back-projection): using the intrinsic matrix K, map pixel (u, v) to a ray in camera coordinates.

   .. math::

      K = \begin{bmatrix}
        f_x & 0 & c_x \\
        0 & f_y & c_y \\
        0 & 0 & 1
      \end{bmatrix}

   Given pixel coordinates \( (u, v) \) and homogeneous form \( \tilde{p} = [u, v, 1]^T \), the normalized camera ray (direction) is

   .. math::

      r_c = K^{-1} \tilde{p} = \begin{bmatrix} x_c \\ y_c \\ 1 \end{bmatrix} ,

   where \(x_c = (u - c_x)/f_x\) and \(y_c = (v - c_y)/f_y\) for a pinhole model with no skew.

4. Rotate ray into ENU/world frame: using the camera-to-ENU rotation \(R_{ce}\), obtain the ray in ENU coordinates

   .. math::

      r_e = R_{ce} \; r_c

   The camera origin in ENU coordinates is the drone position at altitude \(h\): \(p_e = [0, 0, h]^T\) if we place ENU origin at the drone's ground-projected location, or use the true ENU coordinates computed from \(\phi_0, \lambda_0, h_0\).

5. Intersect ray with ground plane (approximate flat Earth locally): assume ground is at altitude \(z = 0\) in ENU frame (or at known ground elevation). Parametric ray from camera origin:

   .. math::

      p_e(t) = p_{cam} + t \; r_e, \qquad t > 0

   Solve for t such that the z-component equals ground altitude z_g (typically 0):

   .. math::

      t^* = \frac{z_g - p_{cam,z}}{r_{e,z}}

   Then the intersection point in ENU is

   .. math::

      P_{enu} = p_{cam} + t^* \; r_e

   Note: if \(r_{e,z} \approx 0\) (ray nearly parallel to ground) the intersection is unstable; handle this edge case by rejecting or using a different method (e.g., local DEM).

6. Convert ENU coordinates to geodetic coordinates (latitude, longitude): given ENU offset \(\Delta E = [e, n, u]^T\) from reference geodetic point \((\phi_0, \lambda_0, h_0)\), convert back to latitude/longitude. For small distances you can use the local flat-earth approximation:

   .. math::

      \Delta \phi \approx \frac{n}{R_N + h_0}, \qquad
      \Delta \lambda \approx \frac{e}{(R_E + h_0) \cos\phi_0}

   where \(R_N\) and \(R_E\) are radii of curvature (or simply use Earth's mean radius R \approx 6371000 m for small offsets). Then

   .. math::

      \phi = \phi_0 + \Delta \phi, \qquad \lambda = \lambda_0 + \Delta \lambda

   For more accurate conversion use a proper ENU <-> ECEF <-> geodetic pipeline (eg. pyproj or GeographicLib).

7. Output estimated GPS coordinates (latitude, longitude) and optionally estimated horizontal uncertainty derived from altitude and detection pixel uncertainty.

Notes and Edge cases
~~~~~~~~~~~~~~~~~~~~~

- Distortion: if distortion is not negligible, undistort the pixel coordinates before back-projection using the distortion coefficients from calibration.
- Altitude reference: ensure the altitude used for camera origin and ground plane (\(z_g\)) are in the same vertical datum (above ellipsoid vs above mean sea level vs above ground). Mismatched vertical references produce biases.
- Attitude accuracy: small errors in pitch/roll cause horizontal errors that increase with altitude; quantify uncertainty accordingly.
- Near-parallel rays: if the ray is parallel to the ground (\(r_{e,z} \approx 0\)), the intersection is unstable — handle by rejecting or using a DEM or optical flow to estimate scale.


.. admonition:: Recommended Reading
   :class: tip

   Check out how we implemented it in the `Nebula GitHub Repository in the (nebula/controls/yolo.py) <https://github.com/amar-jay/nebula/blob/main/nebula/controls/detection/yolo.py>`_ for
   a more practical understanding of the implementation.