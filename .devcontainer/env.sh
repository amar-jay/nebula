#!/bin/bash

# Set the base directory for the workspace
# export MYHOME=/workspaces/nebula
export MYHOME=/teamspace/studios/this_studio/nebula
echo "MYHOME:"
cd $MYHOME
pwd
ls

# ArduPilot-Gazebo plugin version
export GZ_VERSION="garden"

# Set environment variables for Gazebo and ArduPilot integration
export GZ_SIM_SYSTEM_PLUGIN_PATH="$MYHOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/ardupilot_gazebo/models:$MYHOME/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH"
export GZ_SIM_RESOURCE_PATH="$MYHOME/gz_ws/src/sim/models:$MYHOME/gz_ws/src/sim/worlds:$GZ_SIM_RESOURCE_PATH"

#export MESA_GL_VERSION_OVERRIDE=3.3
#export LIBGL_ALWAYS_SOFTWARE=1
#unset MESA_GL_VERSION_OVERRIDE LIBGL_ALWAYS_SOFTWARE
# Optional: Source your environment to make the changes active
#source ~/.bashrc


#glxinfo | grep "OpenGL version"
#glxinfo | grep "OpenGL renderer"
#glxinfo | grep "direct rendering"
echo "Setup of Environment variables complete. OPENGL VERSION MUST BE >=3.3"

