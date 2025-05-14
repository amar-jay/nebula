FROM ubuntu:22.04

# Set noninteractive installation
ENV DEBIAN_FRONTEND=noninteractive
ARG DEBIAN_FRONTEND=noninteractive
ARG USER_UID=1000
ARG USER_GID=1000
ARG SKIP_AP_EXT_ENV=1
ARG SKIP_AP_GRAPHIC_ENV=1
ARG SKIP_AP_COV_ENV=1
ARG SKIP_AP_GIT_CHECK=1
# Home should be current working directory. pwd
ENV HOME=/workspace
ENV USER=manan

# Create a non-root user with sudo privileges
RUN apt-get update && \
	 apt-get upgrade -y && apt-get install -y sudo && \
    useradd -m ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER}

ENV SKIP_AP_EXT_ENV=$SKIP_AP_EXT_ENV SKIP_AP_GRAPHIC_ENV=$SKIP_AP_GRAPHIC_ENV SKIP_AP_COV_ENV=$SKIP_AP_COV_ENV SKIP_AP_GIT_CHECK=$SKIP_AP_GIT_CHECK

# Install basic packages
RUN apt-get update && apt-get install -y \
    apt-utils \
    wget \
    curl \
    xauth \
    build-essential \
    cmake \
    python3 \
    python3-pip \
    python3-dev \
    vim \
    git \
    make \
    tmux \
    locales \
	lsb-release


# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Setup Gazebo repositories
RUN sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list' && \
	 wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -


# Install Gazebo and dependencies
RUN apt-get update && \
    apt-get install -y \
	 gnupg \
	 libgz-sim8-dev \
	 rapidjson-dev \
    libopencv-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-gl 

# Switch to non-root user
USER ${USER}
WORKDIR ${HOME}



# Clone ArduPilot
RUN git clone https://github.com/ArduPilot/ardupilot -b Copter-3.5 && \
    cd ardupilot && \
    git checkout "Copter-4.5" && \
    git submodule update --init --recursive

RUN pip3 install --upgrade pip setuptools wheel

# Install ArduPilot prerequisites
RUN bash -c "${HOME}/ardupilot/Tools/environment_install/install-prereqs-ubuntu.sh -y"

# Set environment variables
ENV GZ_VERSION="harmonic"
ENV GZ_SIM_SYSTEM_PLUGIN_PATH=${HOME}/src/ardupilot_gazebo/build
ENV GZ_SIM_RESOURCE_PATH=${HOME}/src/ardupilot_gazebo/models:${HOME}/src/ardupilot_gazebo/worlds

WORKDIR ${HOME}
ENTRYPOINT ["${HOME}/scripts/entrypoint.sh"]
CMD ["bash"]