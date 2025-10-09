WORLD=delivery_runway.sdf
MODEL=gazebo-iris

# Define the variable name and value
GZ_SIM_SYSTEM_PLUGIN_PATH := $(CURDIR)/nebula/ardupilot_gazebo/build:$$GZ_SIM_SYSTEM_PLUGIN_PATH
GZ_SIM_RESOURCE_PATH := $(CURDIR)/nebula/ardupilot_gazebo/models:$(CURDIR)/nebula/ardupilot_gazebo/worlds:$$GZ_SIM_RESOURCE_PATH


RE_SOURCE_FLAG := /tmp/re_source_needed.flag
define set_env_var_fn
	@if ! grep -qE "^export $(1)" $(HOME)/.bashrc; then \
		echo "export $(1)=\"$(2)\"" >> $(HOME)/.bashrc; \
		echo "$(1) added to .bashrc."; \
		touch $(RE_SOURCE_FLAG); \
	else \
		echo "$(1) already set in .bashrc."; \
	fi
endef

.PHONY: gz app demo_app ardupilot_gz create camera_feed set_env_vars install_tmux \
        gz_sim cpu_info test_cv test_gst test_torch setup build_app test_fps \
        sim_server server sim_server2 recv lint telem k_telem

gz:
	gz sim -v4 -r ${WORLD}

app:
	@python -m nebula.gcs.app

demo_app:
	@python -m nebula.gcs.nebula.main.demo

ardupilot_gz:
	${HOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL} --model JSON --map --console

create:
	bash -c 'source ./setup.sh' >> ./.devcontainer/postCreateCommand.log 2>&1

gz_camera_feed:
	gst-launch-1.0 -v udpsrc port=5600 \
	! application/x-rtp,encoding-name=H264 \
	! rtph264depay \
	! avdec_h264 \
	! videoconvert \
	! videorate \
	! video/x-raw,framerate=30/1 \
	! autovideosink

# Check if the variable is defined and add it to .bashrc if it's not
set_env_vars:
	@rm -f $(RE_SOURCE_FLAG)
	$(call set_env_var_fn,GZ_VERSION,harmonic)
	$(call set_env_var_fn,GZ_SIM_SYSTEM_PLUGIN_PATH,$(GZ_SIM_SYSTEM_PLUGIN_PATH))
	$(call set_env_var_fn,GZ_SIM_RESOURCE_PATH,$(GZ_SIM_RESOURCE_PATH))
	@bash -c 'if [ -f "$(RE_SOURCE_FLAG)" ]; then source $(HOME)/.bashrc; fi'

install_tmux: # completely unrelated to the project, but I think its useful to have
	curl -s https://gist.githubusercontent.com/amar-jay/ba9e5a475e1f0fe04b6ff3f4c721ba43/raw | bash

gz_sim:
	@./scripts/run_sim.sh -w ${WORLD}
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

build_app:
	printf "from nebula.gcs.app import main\nif __name__ == '__main__':\n    main()\n" > app.py
	pyinstaller app.spec
	rm app.py

test_fps:
	python -m scripts.check_fps

sim_server:
	@python -m nebula.mq.zmq_server --is-simulation

server:
	@python -m nebula.mq.zmq_server

sim_server2:
	@python -m nebula.mq.zmq_server-experimentalv2 --is-simulation

recv:
	@python -m nebula.mq.example_zmq_reciever

lint:
	@isort .
	@black .

telem:
	mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --console --out=udp:127.0.0.1:14550

k_telem:
	mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --console --out=udp:127.0.0.1:14560


