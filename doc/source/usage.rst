Usage
=====

.. _techspecs:

Specifications
------------------------

+------------------------+------------------------+------------------------------------------------------------+
| **Component**          | **Version**            | **Dependencies**                                           |
+========================+========================+============================================================+
| Flight Controller      | ArduPilot Copter 4.3   | ArduPilot                                                  |
+------------------------+------------------------+------------------------------------------------------------+
| Communication Protocol | MAVLink 2.0            | pymavlink 2.4.37                                           |
+------------------------+------------------------+------------------------------------------------------------+
| Edge Runtime           | Ubuntu 22.04           | Python 3.10                                                |
+------------------------+------------------------+------------------------------------------------------------+
| Vision Backend         | YOLOv8                 | OpenCV(v4), PyTorch (v2.7)                                 |
+------------------------+------------------------+------------------------------------------------------------+
| UI Framework           | PySide6                | QFluentWidgets                                             |
+------------------------+------------------------+------------------------------------------------------------+

.. note::

   **Hardware Requirements:** CUDA-enabled GPU for vision processing, 8 GB RAM minimum.


.. _installation:

Installation
------------

1. **Clone the repository** (uses Git submodules):

   .. code-block:: bash

      git clone https://github.com/amar-jay/nebula.git --recursive

2. **Setup ArduPilot**:

   - Follow `ArduPilot Linux setup guide <https://ardupilot.org/dev/docs/building-setup-linux.html>`_
   - Follow `Gazebo and GStreamer setup guide <https://ardupilot.org/dev/docs/sitl-with-gazebo.html#sitl-with-gazebo>`_

3. Install OpenCV (if not already installed - preferably from source):

   .. code-block:: bash

      sudo apt-get install libopencv-dev python3-opencv

3. **Run setup script**:

   .. code-block:: bash

      make setup

3. **Install Python packages** (package version might be incompatible with your system, use virtual environment, and adjust package versions if needed):

   .. code-block:: bash

      python3 -m venv .venv
      source .venv/bin/activate
      pip install --upgrade pip
      pip install -r requirements.txt

4. **Set Environment Variables**:

   .. code-block:: bash

      make set_env_vars

5. **Build** ``src/ardupilot_gazebo`` using CMake (optional if not working in simulation):

   .. code-block:: bash

      cd src/ardupilot_gazebo
      mkdir build
      cd build
      cmake ..
      make -j4
      cd ../../../..

Running the Simulation
----------------------

1. **Start simulation**:

   .. code-block:: bash

      make run_sim

2. **Launch Control Station**:

   .. code-block:: bash

      make app

3. **Launch Controls** (optional):

   .. code-block:: bash

      make sim_server  # for real drone use `make server`

