#!/bin/bash
set -e

cd ${HOME}
git submodule update --remote --merge
git submodule update --init --recursive

# Source environment variables
make set_env_vars


# Display OpenGL info
# echo "Checking OpenGL configuration..."
# if [ -n "$DISPLAY" ]; then
#   glxinfo | grep "OpenGL version" || echo "OpenGL info not available"
# else
#   echo "DISPLAY not set, skipping OpenGL check"
# fi

cd ${HOME}/src/ardupilot_gazebo && \
	mkdir -p build && \
	cd build && \
	cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo

source $HOME/.bashrc

cd ${HOME}
bash ./scripts/run_sim.sh 