MYHOME=/workspaces/robotics_template
WORLD=iris_runway.sdf
MODEL=gazebo-iris

gz:
	gz sim -v4 -r ${WORLD} 

ardupilot_gz:
	${MYHOME}/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f ${MODEL} --model JSON --map --console


create:
	bash -c 'source ./.devcontainer/setup.sh' >> ./.devcontainer/postCreate.log 2>&1
