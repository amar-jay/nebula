#!/bin/bash

# Set the base directory for the workspace
export MYHOME=$PWD
sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
sudo apt-get update
sudo apt upgrade -y

# Install Gazebo 11 (Harmonic) and dependencies
sudo apt-get install -y xauth x11-apps x11-common build-essential cmake git lsb-release wget
sudo apt install -y libgz-sim8-dev rapidjson-dev libopencv-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
  libgl1-mesa-dev  libgl1-mesa-dri  libgl1-mesa-glx \
  mesa-utils

# install tmux
bash <(curl -s https://gist.githubusercontent.com/amar-jay/ba9e5a475e1f0fe04b6ff3f4c721ba43/raw)

# Clone and set up ArduPilot repository
if [ -d "$HOME/ardupilot" ]; then
    echo "ArduPilot directory already exists. Skipping clone."
    cd $HOME/ardupilot
else
    git clone https://github.com/ArduPilot/ardupilot $HOME/ardupilot
    cd $HOME/ardupilot
    git checkout "Copter-4.5"

git submodule update --init --recursive

# Install ArduPilot prerequisites
$HOME/ardupilot/Tools/environment_install/install-prereqs-ubuntu.sh -y

# Build the ArduPilot-Gazebo plugin
export GZ_VERSION="harmonic"
cd $MYHOME/src/ardupilot_gazebo
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j4

# Set environment variables for Gazebo and ArduPilot integration
cd $MYHOME # go to currrent repo
make set_env_vars

echo "Setup complete! Gazebo and ArduPilot-Gazebo integration are ready."

