# MATEK

### Features

- **Advanced Simulation**: Nebula leverages Gazebo and ArduPilot to provide realistic simulation environments for autonomous vehicles.
- **Control Station**: A user-friendly control station interface built with PyQt5 for monitoring and controlling the autonomous vehicles.
- **Machine Learning Integration**: Integration with PyTorch and YOLO for advanced machine learning capabilities, including object detection and tracking.
- **Modular Architecture**: The project is designed with a modular architecture, allowing for easy extension and customization.

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
```


## Usage Instructions

### Running the Simulation

1. **Run Simulation**: Use the provided script to start the Gazebo simulation.
   ```bash
   ./run_sim.sh -w <world_file.sdf>
   ```

### Using the Control Station

1. **Launch the Control Station**: Use the provided script to launch the control station interface.
   ```bash
   python src/control_station
   ```


1. **Launch Controls**: Use the provided script to launch the control software
   ```bash
   python src/controls
   ```

## Technologies and Frameworks Used

- **Gazebo**: A powerful simulation tool for robotics and autonomous systems.
- **ArduPilot**: An open-source autopilot system supporting various types of vehicles.
- **PyQt5**: We are planning to change to PySide6
- **PyTorch**: An open-source machine learning library for Python, used for integrating machine learning capabilities.
- **YOLO**: A state-of-the-art object detection system, used for detecting and tracking objects in the simulation.
