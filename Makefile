# MYHOME=/workspaces/nebula
MYHOME=/teamspace/studios/this_studio/nebula

WORLD=our_runway.sdf
#WORLD=gimbal.sdf
MODEL=gazebo-iris
#MODEL=iris_with_gimbal


# Define the variable name and value
GZ_SIM_SYSTEM_PLUGIN_PATH := $$HOME/Desktop/code/matek/src/ardupilot_gazebo/build:$$GZ_SIM_SYSTEM_PLUGIN_PATH
GZ_SIM_RESOURCE_PATH := $$HOME/Desktop/code/matek/src/ardupilot_gazebo/models:$$HOME/Desktop/code/matek/src/ardupilot_gazebo/worlds:$$GZ_SIM_RESOURCE_PATH

define set_env_var_fn
	@if [ -z "$$$(grep -E "^export $(1)=" ~/.bashrc)" ]; then \
		echo "$(1) is not set in .bashrc."; \
		echo "Adding $(1) to .bashrc..."; \
		echo "export $(1)=\"$(2)\"" >> ~/.bashrc; \
		echo "$(1) added to .bashrc."; \
	else \
		echo "$(1) is already defined in .bashrc."; \
	fi
endef

gz:
	gz sim -v4 -r ${WORLD} 

ardupilot_gz:
	${MYHOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL} --model JSON --map --console

create:
	bash -c 'source ./setup.sh' >> ./.devcontainer/postCreateCommand.log 2>&1

camera_feed:
	gst-launch-1.0 -v udpsrc port=5600 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! avdec_h264 ! videoconvert ! jpegenc ! multipartmux ! tcpserversink host=0.0.0.0 port=8080


# Check if the variable is defined and add it to .bashrc if it's not
set_env_vars:
	$(call set_env_var_fn,GZ_SIM_SYSTEM_PLUGIN_PATH,$(GZ_SIM_SYSTEM_PLUGIN_PATH))
	$(call set_env_var_fn,GZ_SIM_RESOURCE_PATH,$(GZ_SIM_RESOURCE_PATH))
