---
template: frontpage.html

hide:
  - toc
---

[![System Demo](https://img.youtube.com/vi/ZF_N-Vu7Tik/maxresdefault.jpg)](https://www.youtube.com/watch?v=ZF_N-Vu7Tik){ width="25%" height="auto" target="_blank" rel="noopener" }

# Nebula 2025 Drone System

## System Architecture

<div class="grid cards" markdown>

-   ### :material-monitor: Ground Control Station
    ----

    Primary control interface for drone monitoring, command transmission, and mission oversight

    **Core Components**  
    - PySide6/QFluentWidgets UI framework  
    - MAVLink telemetry visualization  
    - Mission planning interface  
    - Emergency command pipeline  
    
    [:octicons-arrow-right-24: Module Documentation](gcs/index.md)

-   ### :material-connection: Communications
    ----

    Handles all inter-module communication between edge server and GCS

    **Core Components**  
    - ZeroMQ message broker  
    - Asyncio task manager  
    - MAVLink protocol implementation  
    
    [:octicons-arrow-right-24: Module Documentation](comms/index.md)

-   ### :material-brain: Image Processing
    ----

    Computer vision subsystem for target identification and payload operations

    **Core Components**  
    - YOLOv8 object detection  
    - OpenCV preprocessing  
    - GPS estimation system  
    
    [:octicons-arrow-right-24: Module Documentation](vision/index.md)

-   ### :material-airplane: Simulation
    ----
    Complete hardware-in-loop testing environment

    **Core Components**  
    - Gazebo environment  
    - ArduPilot SITL  
    - Sensor emulation  
    
    [:octicons-arrow-right-24: Module Documentation](simulation/index.md)
</div>


<div class="" markdown style="padding: 0 1em 0 1em;">
[LICENSE](#) | [Issue Tracker](https://github.com/amar-jay/nebula/issues)
</div>

---

## Project Overview

This documentation covers the Nebula 2025 autonomous drone system developed for the [Teknofest 2025 Drone Competition](https://www.teknofest.org). The system features:

- Real-time drone control via PySide6-based Ground Station
- On-edge processing with ZeroMQ communication
- ArduPilot integration for flight control
- Computer vision for package loading operations
- Gazebo simulation environment



## Teknofest

[Teknofest](https://www.teknofest.org) is Turkey's premier aerospace and technology festival featuring competitive categories across multiple engineering disciplines. Our 10-member team developed this system for the drone competition category, focusing on autonomous package delivery and object recognition tasks.


### Technical Software Leadership
Documentation and system architecture led by [amarjay](https://github.com/amar-jay)

---

## Technical Specifications
| Component              | Version       | Dependencies          |
|------------------------|---------------|-----------------------|
| Flight Controller      | ArduPilot Copter 4.3 | Ardupilot   |
| Communication Protocol | MAVLink 2.0   | pymavlink 2.4.37      |
| Edge Runtime           | Ubuntu 22.04  | Python 3.10  |
| Vision Backend         | YOLOv8       | OpenCV, PyTorch       |
| GCS Framework          | PySide6       | QFluentWidgets [(amar-jay's fork)](https://github.com/amar-jay/QFluentWidgets)  |

## Getting Started
```bash
git clone --recurse-submodules https://github.com/amar-jay/nebula.git
cd nebula
git submodule update --init --recursive
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make run_sim  # Launch simulation
make app      # Start control station
make sim_server # Start edge server (simulation mode)
```

> **Hardware Requirements:** CUDA-enabled GPU for vision processing, 8GB RAM minimum


---
