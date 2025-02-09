MYHOME=/workspaces/nebula
WORLD=our_runway.sdf
#WORLD=gimbal.sdf
MODEL=gazebo-iris
#MODEL=iris_with_gimbal

gz:
	gz sim -v4 -r ${WORLD} 

ardupilot_gz:
	${MYHOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL} --model JSON --map --console

create:
	bash -c 'source ./setup.sh' >> ./.devcontainer/postCreateCommand.log 2>&1

camera_feed:
	gst-launch-1.0 -v udpsrc port=5600 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! avdec_h264 ! videoconvert ! jpegenc ! multipartmux ! tcpserversink host=0.0.0.0 port=8080
