Gazebo Simulation
==============

.. _simulation:

The `Gazebo simulation <https://github.com/amar-jay/gazebo-sitl>`_ used in Nebula is based on a fork of the `official ArduPilot Gazebo SITL plugin <https://github.com/ArduPilot/ardupilot_gazebo>`_.
This fork has a couple of alterations and customizations for our usecase (such as more worlds as assets as well as nadir camera support).
Also, this fork has multi-drone-flight support.


Setup
----------------

To set up the Gazebo simulation environment, you need to install the necessary dependencies. You can do this by running the following commands in your terminal:

.. code-block:: bash

		sudo apt update
		sudo apt install libgz-sim8-dev rapidjson-dev
		sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl

You can also use rosdep if you have ROS installed:

.. code-block:: bash

		export GZ_VERSION=harmonic

		sudo bash -c 'wget https://raw.githubusercontent.com/osrf/osrf-rosdep/master/gz/00-gazebo.list -O /etc/ros/rosdep/sources.list.d/00-gazebo.list'

		rosdep update
		rosdep resolve gz-harmonic
		# Navigate to your ROS workspace if using catkin/colcon
		rosdep install --from-paths src --ignore-src -y

To ensure that Gazebo can locate the necessary plugins and models, you need to set the following environment variables in your shell configuration file (e.g., ``~/.bashrc`` or ``~/.zshrc``):

.. code-block:: bash

		export GZ_VERSION=harmonic
		export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}
		export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}

.. note::

	 However, if you are using it together with the `Nebula Project <https://github.com/amar-jay/nebula>`_, as a whole
	 just by running ``make setup`` within the Nebula repository should install all necessary dependencies and set it up seemlessly. 

An important thing to note is that the Gazebo version should be compatible with the ArduPilot version you are using.
For example, ArduPilot 4.3+ works well with Gazebo 11 and ArduPilot 4.4+ works well with Gazebo 9.
Refer to the `official ArduPilot documentation <https://ardupilot.org/dev/docs/sitl-with-gazebo.html>`_ for more details on version compatibility.



Camera Configuration
---------------------

The Gazebo simulation includes a downward-facing camera mounted on the drone.
This camera is configured in the drone's SDF (Simulation Description Format) file, which can be found in the 
:c:`ardupilot_gazebo/models/iris <https://github.com/amar-jay/gazebo_sitl/blob/main/models/iris_with_gimbal/model.sdf>` directory. 
You can modify the camera parameters such as resolution, field of view, and update rate in the 
:c:`ardupilot_gazebo/models/gimbal_small_1d <https://github.com/amar-jay/gazebo_sitl/blob/main/models/gimbal_small_1d/model.sdf#L112>` directory. 
There is no need to modify the code anywhere else it will able to pick up the changes automatically and work seamlessly in the Nebula project.

.. warning::
   Some parts of the codebase contain **sensitive logic or proprietary information**.  
   Exercise caution when reading or modifying these sections.

A quick way to view the camera feed is to use the following command:

.. code-block:: bash

	gst-launch-1.0 -v udpsrc port=5600 \
  	caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' \
    ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false


In viewing the camera feed, you might notice a slight delay (latency) due to the video streaming process. This is normal and expected in most simulation environments.
To simulate at high-speed or in real-time, you can adjust the simulation speed using the following command within the SDF file:

.. code-block:: xml

		<physics name="1ms" type="ignore">
		  <max_step_size>0.001</max_step_size>
		  <real_time_factor>-1.0</real_time_factor>
		</physics>

.. note::

		At times there are issues with the GStreamer backend of OpenCV. If you encounter problems with the camera feed, you can try rebuilding OpenCV from source with GStreamer support enabled.

		You can verify if OpenCV has GStreamer support by running the command `make test_cv` which shows all the 
		supported backends that is on your OpenCV build. If GStreamer is listed, then it has support.

		Alternatively, you can use the following Python script to test the GStreamer pipeline with OpenCV:

		.. code-block:: python

				import cv2

				pipeline = (
				    "udpsrc port=5600 ! "
				    "application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! "
				    "rtph264depay ! "
				    "h264parse ! "
				    "avdec_h264 ! "
				    "videoconvert ! "
				    "appsink drop=1"
				)

				cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

				if not cap.isOpened():
				    print("Failed to open stream! Check sender or pipeline.")
				    exit()

				while True:
				    ret, frame = cap.read()
				    if not ret:
				        print("Failed to read frame.")
				        break

				    cv2.imshow("Stream", frame)
				    if cv2.waitKey(1) & 0xFF == ord('q'):
				        break

				cap.release()
				cv2.destroyAllWindows()


Worlds
----------------

There are multiple worlds available in the Gazebo simulation for different testing scenarios.
You can find these worlds in the ``ardupilot_gazebo/worlds`` directory. Some of the available worlds include:

- **delivery_runway (default)**: A runway environment designed for delivery drone simulations with multiple drones, helipads and a tank for detection.

- **iris_runway**: The default world that comes with the ArduPilot Gazebo plugin, featuring a runway for takeoff and landing.

- **our_runway**: Iris runway with an added helipad for landing tests and drone stabilization and especially for GPS estimation testing.

- **farm**: An animal farm environment with various farm animals and structures.

- **orchard**: A world with trees and natural terrain, suitable for testing navigation and obstacle avoidance.

- **gimbal**: An iris runway with a gimbal camera setup for viewing over the horizon.


Alternative Camera Streaming 
-----------------------------

Due to the inherent latency in GStreamer, you might want to explore alternative methods for streaming the camera feed.
One such method is using `ROS2 <https://docs.ros.org/en/foxy/index.html>`_ with the `image_transport <https://docs.ros.org/en/foxy/api/image_transport/html/index.html>`_ package.


.. admonition:: Recommended Reading
   :class: tip

   Please refer to the `Nebula GitHub README <https://github.com/amar-jay/nebula>`_  
   as well as the `Nebula ArduPilot Gazebo Fork <https://github.com/amar-jay/gazebo-sitl>`_  
   for the most up-to-date setup, usage instructions, and system overview.
