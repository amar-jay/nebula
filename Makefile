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

RUNWAY:=delivery_runway
MODEL_NAME:=iris_with_stationary_gimbal
CAMERA_LINK:=tilt_link

app:
	@python -m src.gcs.app

demo_app:
	@python -m src.gcs.src.main.demo

gz:
	gz sim -v4 -r ${RUNWAY}.sdf

ardupilot_gz:
	${HOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL_NAME} --model JSON --map --console

create:
	bash -c 'source ./setup.sh' >> ./.devcontainer/postCreateCommand.log 2>&1

camera_feed: enable_streaming
	gst-launch-1.0 -v udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)h264' ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false

raw_camera_stream: enable_streaming
	@ffmpeg -fflags nobuffer -flags low_delay -strict experimental \
    -protocol_whitelist file,udp,rtp \
    -i scripts/gazebo_stream.sdp \
    -c:v copy -rtsp_transport tcp \
    -f rtsp rtsp://127.0.0.1:8554/raw >/dev/null 2>&1

my_camera_stream:
	@ffmpeg -f v4l2 -framerate 30 -video_size 1280x720 -i /dev/video0 \
				-vcodec libx264 -preset ultrafast -tune zerolatency \
				-f rtsp rtsp://127.0.0.1:8554/raw >/dev/null 2>&1


# ! video/x-raw,framerate=60/1
set_env_vars: # Check if the variable is defined and add it to .bashrc if it's not
	@rm -f $(RE_SOURCE_FLAG)
	$(call set_env_var_fn,GZ_VERSION,harmonic)
	$(call set_env_var_fn,GZ_SIM_SYSTEM_PLUGIN_PATH,$(GZ_SIM_SYSTEM_PLUGIN_PATH))
	$(call set_env_var_fn,GZ_SIM_RESOURCE_PATH,$(GZ_SIM_RESOURCE_PATH))
	@bash -c 'if [ -f "$(RE_SOURCE_FLAG)" ]; then source $(HOME)/.bashrc; fi'

install_tmux: # completely unrelated to the project, but I think its useful to have
	curl -s https://gist.githubusercontent.com/amar-jay/ba9e5a475e1f0fe04b6ff3f4c721ba43/raw | bash

gz_sim:
	@./scripts/run_sim.sh -w ${RUNWAY}.sdf

cpu_info:
	@python ./scripts/cpu_info.py

test_cv:
	@python ./scripts/test_cv.py

test_gst:
	@gst-launch-1.0 v4l2src ! videoconvert ! autovideosink

enable_streaming:
	@echo "$(CAMERA_LINK) for $(RUNWAY) in $(MODEL_NAME)"
	@gz topic -t /world/$(RUNWAY)/model/$(MODEL_NAME)/model/gimbal/link/$(CAMERA_LINK)/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p "data: 1"

test_torch: # not sure if this is needed, only endpoint is in YOLO
	@python ./scripts/test_torch.py

setup:
	@./scripts/setup.sh

build_app:
	printf "from src.gcs.app import main\nif __name__ == '__main__':\n    main()\n" > app.py
	pyinstaller app.spec
	rm app.py

test_fps:
	python -m scripts.check_fps

sim_server_zmq:
	@python -m src.mq.zmq_server --is-simulation

server_zmq:
	@python -m src.mq.zmq_server

local_server_zmq:
	@python -m src.mq.local_detection

local_sim_server_zmq:
	@python -m src.mq.local_detection --is-simulation

sim_server:
	@bash -c '\
		cleanup() { \
			echo "Killing servers..."; \
			[ -n "$$MEDIAMTX_PID" ] && kill $$MEDIAMTX_PID 2>/dev/null; \
			[ -n "$$SERVER_PID" ] && kill $$SERVER_PID 2>/dev/null; \
			exit; \
		}; \
		trap cleanup SIGINT SIGTERM; \
		./mediamtx & \
		MEDIAMTX_PID=$$!; \
		$(MAKE) sim_server_zmq & \
		SERVER_PID=$$!; \
		wait $$MEDIAMTX_PID $$SERVER_PID \
	'

server:
	@bash -c '\
		cleanup() { \
			echo "Killing servers..."; \
			[ -n "$$MEDIAMTX_PID" ] && kill $$MEDIAMTX_PID 2>/dev/null; \
			[ -n "$$SERVER_PID" ] && kill $$SERVER_PID 2>/dev/null; \
			exit; \
		}; \
		trap cleanup SIGINT SIGTERM; \
		./mediamtx & \
		MEDIAMTX_PID=$$!; \
		$(MAKE) server_zmq & \
		SERVER_PID=$$!; \
		wait $$MEDIAMTX_PID $$SERVER_PID \
	'

lint:
	@isort .
	@ruff format .
	@black .

telem:
	mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --console --out=udp:127.0.0.1:14550

k_telem:
	mavproxy.py --master=/dev/ttyUSB1 --baudrate=57600 --console --out=udp:127.0.0.1:14560
