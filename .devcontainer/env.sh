#!/bin/bash

# Set the base directory for the workspace
export MYHOME="/workspaces/robotics_template"

# ArduPilot-Gazebo plugin version
export GZ_VERSION="garden"

# Set environment variables for Gazebo and ArduPilot integration
export GZ_SIM_SYSTEM_PLUGIN_PATH="$MYHOME/gz_ws/src/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/gz_ws/src/ardupilot_gazebo/models:$MYHOME/gz_ws/src/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/gz_ws/src/sim/models:$MYHOME/gz_ws/src/sim/worlds:$GZ_SIM_RESOURCE_PATH"

export MESA_GL_VERSION_OVERRIDE=3.3
export LIBGL_ALWAYS_SOFTWARE=1

# Optional: Source your environment to make the changes active
#source ~/.bashrc

glxinfo | grep "OpenGL version"
echo "Setup of Environment variables complete."

