# MATEK

### Features

- **Control Station**: built for monitoring and controlling the drone.
- **Gazebo Simulation**: Gazebo and ArduPilot
- **Controls**: built for monitoring and controlling the drone.
   - **Machine Learning Integration**: For object detection and monitoring.
   - **GPS Coordinate estimation**
  
## Comprehensive Setup Instructions

### Prerequisites

- **Operating System**: Ubuntu 22.04 or later
- **Dependencies**: Git, Python, Gazebo, ArduPilot, PyTorch, OpenCV

### Cloning the Repository

This project uses **Git submodules**, so make sure to follow the correct steps when cloning and setting up the repository.

```bash
git clone --recurse-submodules https://github.com/amar-jay/nebula.git
cd nebula
git submodule update --remote --merge
git submodule update --init --recursive
```

### Install Python Packages

```bash
pip install -r requirements.txt
```

## Usage Instructions

### Running the Simulation

1. Running control software
   a. **For Simulation**: Use the provided script to start the Gazebo simulation.
   ```bash
      ./run_sim.sh -w <world_file.sdf>
   ```
   b. **For Drone**: Not a stable version (Currently experimental-to check if it can work across herelink)
   ```bash
      python -m src.mq.example_zmq_server # running a zmq server where pymavlink is ported over TCP and actions and video frames sent over ZMQ
   ```
3. **Launch the Control Station**: Use the provided script to launch the control station interface.
   ```bash
      make app
   ```

4. **Launch Controls**: Use the provided script to launch the control software
   ```bash
   python src/controls
   ```


## Technologies and Frameworks Used

- **Gazebo**: A simulation tool for robotics and autonomous systems.
- **ArduPilot**: An open-source autopilot system supporting various types of vehicles.
- **PySide6**: Our applicaation is built with PySide6 using the qfluentwidget library (We also use a modified version of it -- not in this repo)
- **YOLO**: An object detection system, used for detecting and tracking objects in the simulation.

### Commands
```bash
python3 -m src.controls.mavlink.gz # test gazebo simulation and video streaming
```

```bash
python -m src.mq.example_zmq_server # running an example zmq server where pymavlink is ported over TCP and actions and video frames sent over ZMQ

python -m src.mq.example_zmq_server --is-simulation # this is the simulation version of the zmq server
```


```bash
python -m src.mq.example_zmq_reciever # the client of the zmq server.
```

```bash
make app # to run the Ground Control Station Application
```
