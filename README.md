# Project Nebula

## Detailed Project Description

Nebula is a cutting-edge project aimed at providing advanced simulation and control capabilities for autonomous vehicles, particularly drones. The project integrates various technologies and frameworks to create a comprehensive environment for testing, training, and deploying autonomous systems. The primary goal of Nebula is to facilitate the development and deployment of autonomous vehicles by providing a robust and flexible simulation platform.

### Features

- **Advanced Simulation**: Nebula leverages Gazebo and ArduPilot to provide realistic simulation environments for autonomous vehicles.
- **Control Station**: A user-friendly control station interface built with PyQt5 for monitoring and controlling the autonomous vehicles.
- **Machine Learning Integration**: Integration with PyTorch and YOLO for advanced machine learning capabilities, including object detection and tracking.
- **Modular Architecture**: The project is designed with a modular architecture, allowing for easy extension and customization.

## Comprehensive Setup Instructions

### Prerequisites

- **Operating System**: Ubuntu 18.04 or later
- **Dependencies**: Git, Docker, Python, Gazebo, ArduPilot, PyTorch, YOLO

### Cloning the Repository

This project uses **Git submodules**, so make sure to follow the correct steps when cloning and setting up the repository.

```bash
git clone --recurse-submodules https://github.com/amar-jay/nebula.git
cd nebula
git submodule update --remote --merge
```

### Setting Up the Development Environment

1. **Install Docker**: Follow the instructions on the [Docker website](https://docs.docker.com/get-docker/) to install Docker on your system.
2. **Build the Docker Image**: Use the provided Dockerfile to build the Docker image.
   ```bash
   cd .devcontainer
   docker build -t nebula:latest -f _Dockerfile .
   ```
3. **Run the Docker Container**: Start the Docker container with the necessary environment variables.
   ```bash
   docker run -it --rm --name nebula -v $(pwd):/workspace -w /workspace nebula:latest
   ```

## Usage Instructions

### Running the Simulation

1. **Start Gazebo**: Use the provided script to start the Gazebo simulation.
   ```bash
   ./run_sim.sh -w <world_file.sdf>
   ```
2. **Start ArduPilot**: Use the provided script to start the ArduPilot simulation.
   ```bash
   ./run_sim.sh -v
   ```

### Using the Control Station

1. **Launch the Control Station**: Use the provided script to launch the control station interface.
   ```bash
   python src/control_station/__main__.py
   ```

## Project Structure and Directory Layout

```
nebula/
├── .devcontainer/
│   ├── _Dockerfile
│   ├── devcontainer.json
│   ├── env.sh
│   └── postCreateCommand.log
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       └── testing.yml
├── detection/
│   ├── test_torch.py
│   └── train_yolo.py
├── src/
│   ├── control_station/
│   │   ├── __main__.py
│   │   ├── config.py
│   │   └── ui/
│   │       ├── demo.py
│   │       ├── ui_initial_page.py
│   │       ├── ui_splash_main.py
│   │       └── ui_splash_screen.py
│   ├── mq/
│   │   ├── messages.py
│   │   └── workqueue.py
│   └── controls/
├── LICENSE
├── Makefile
├── README.md
├── run_sim.sh
└── setup.sh
```

## Use Cases and Potential Applications

Nebula can be used in various scenarios, including but not limited to:

- **Research and Development**: Researchers can use Nebula to test and validate new algorithms for autonomous vehicles in a controlled and simulated environment.
- **Education**: Educational institutions can leverage Nebula to teach students about autonomous systems, robotics, and machine learning.
- **Industry**: Companies can use Nebula to develop and test autonomous vehicle solutions before deploying them in real-world scenarios.

## Technologies and Frameworks Used

- **Gazebo**: A powerful simulation tool for robotics and autonomous systems.
- **ArduPilot**: An open-source autopilot system supporting various types of vehicles.
- **PyQt5**: A set of Python bindings for Qt libraries, used for building the control station interface.
- **PyTorch**: An open-source machine learning library for Python, used for integrating machine learning capabilities.
- **YOLO**: A state-of-the-art object detection system, used for detecting and tracking objects in the simulation.
