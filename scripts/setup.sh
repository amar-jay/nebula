#!/bin/bash

# Set the base directory for the workspace
# export MYHOME=/workspaces/nebula
export MYHOME=/teamspace/studios/this_studio/nebula
# Update package list and install essential dependencies
# https://gazebosim.org/api/sim/7/install.html
sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
sudo apt-get update
sudo apt upgrade -y

# Install Gazebo 11 (Garden) and dependencies
sudo apt-get install -y xauth x11-apps x11-common build-essential cmake git lsb-release wget
sudo apt install -y libgz-sim7-dev rapidjson-dev libopencv-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
  libgl1-mesa-dev  libgl1-mesa-dri  libgl1-mesa-glx \
  mesa-utils


    # Clone and set up ArduPilot repository
cd $MYHOME
git clone https://github.com/ArduPilot/ardupilot
cd ardupilot
git checkout "Copter-4.5"

# Initialize and update submodules
git submodule update --init --recursive

# Install ArduPilot prerequisites
$MYHOME/ardupilot/Tools/environment_install/install-prereqs-ubuntu.sh -y

# Set up the Gazebo workspace for ArduPilot-Gazebo integration
# mkdir -p $MYHOME/gz_ws/src
cd $MYHOME
git clone https://github.com/ArduPilot/ardupilot_gazebo

# Build the ArduPilot-Gazebo plugin
export GZ_VERSION="garden"
cd $MYHOME/ardupilot_gazebo
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j4

# Set environment variables for Gazebo and ArduPilot integration
export GZ_SIM_SYSTEM_PLUGIN_PATH="$MYHOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/ardupilot_gazebo/models:$MYHOME/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/gz_ws/src/sim/models:$MYHOME/gz_ws/src/sim/worlds:$GZ_SIM_RESOURCE_PATH"

export MESA_GL_VERSION_OVERRIDE=3.3
export LIBGL_ALWAYS_SOFTWARE=1

# Optional: Source your environment to make the changes active
echo "source $MYHOME/.devcontainer/env.sh">> ~/.zshrc

# zsh
glxinfo | grep "OpenGL version"
echo "Setup complete! Gazebo and ArduPilot-Gazebo integration are ready."

