WORLD=our_runway.sdf
#WORLD=gimbal.sdf
MODEL=gazebo-iris
#MODEL=iris_with_gimbal

# Define the variable name and value
GZ_SIM_SYSTEM_PLUGIN_PATH := $(CURDIR)/src/ardupilot_gazebo/build:$$GZ_SIM_SYSTEM_PLUGIN_PATH
GZ_SIM_RESOURCE_PATH := $(CURDIR)/src/ardupilot_gazebo/models:$(CURDIR)/src/ardupilot_gazebo/worlds:$$GZ_SIM_RESOURCE_PATH

#HERE=$(pwd -P) # Absolute path of current directory

RE_SOURCE_FLAG := /tmp/re_source_needed.flag
define set_env_var_fn
	@if ! grep -qE "^export $(1)" $(HOME)/.bashrc; then \
		echo 'export $(1)="$(2)"' >> $(HOME)/.bashrc; \
		echo "$(1) added to .bashrc."; \
		touch $(RE_SOURCE_FLAG); \
	else \
		echo "$(1) already set in .bashrc."; \
	fi
endef


gz:
	gz sim -v4 -r ${WORLD} 

ardupilot_gz:
	${HOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL} --model JSON --map --console

create:
	bash -c 'source ./setup.sh' >> ./.devcontainer/postCreateCommand.log 2>&1

camera_feed:
	gst-launch-1.0 -v udpsrc port=5600 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! avdec_h264 ! videoconvert ! jpegenc ! multipartmux ! tcpserversink host=0.0.0.0 port=8080


# Check if the variable is defined and add it to .bashrc if it's not
set_env_vars:
	@rm -f $(RE_SOURCE_FLAG)
	$(call set_env_var_fn,GZ_VERSION,harmonic)
	$(call set_env_var_fn,GZ_SIM_SYSTEM_PLUGIN_PATH,$(GZ_SIM_SYSTEM_PLUGIN_PATH))
	$(call set_env_var_fn,GZ_SIM_RESOURCE_PATH,$(GZ_SIM_RESOURCE_PATH))
	@bash -c 'if [ -f "$(RE_SOURCE_FLAG)" ]; then source $(HOME)/.bashrc; fi'

install_tmux: # completely unrelated to the project, but I think its useful to have
	curl -s https://gist.githubusercontent.com/amar-jay/ba9e5a475e1f0fe04b6ff3f4c721ba43/raw | bash

run-dev:
	docker run -it --rm \
	--env="DISPLAY=$DISPLAY" \
	--volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
	--volume="$(pwd):/home/developer/matek" \
	ardupilot-gazebo-dev

run_sim:
	@./scripts/run_sim.sh

cpu_info:
	@python ./scripts/cpu_info.py

test_cv:
	@python ./scripts/test_cv.py

test_gst:
	@python ./scripts/camera_display.py

test_torch: # not sure if this is needed, only endpoint is in YOLO
	@python ./scripts/test_torch.py

setup:
	@./scripts/setup.sh

app:
	@python -m src.example_gcs

.PHONY: gz ardupilot_gz create camera_feed set_env_vars install_tmux run-dev run_sim cpu_info test_cv test_gst test_torch setup