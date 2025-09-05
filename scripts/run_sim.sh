#!/bin/bash

usage() {
  echo "Usage: $0 [-v] [-w <world_file.sdf>] [-s]"
  echo "  -v               Enable verbose"
  echo "  -w <file.sdf>    Specify world file to load"
  echo "  -s               Run in simulation mode (start mediamtx)"
  echo "Example:"
  echo "  $0 -v -w iris_runway.sdf -s"
  exit 1
}

VERBOSE=0
WORLD_FILE=""
IS_SIMULATION=false

while getopts ":vw:s" opt; do
  case $opt in
    v) VERBOSE=1 ;;
    w) WORLD_FILE="$OPTARG" ;;
    s) IS_SIMULATION=true ;;
    *) usage ;;
  esac
done

[ -z "$WORLD_FILE" ] && usage

ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --custom-location=40.9588862,29.1357976,15,0 --model JSON --console --instance=0"
MINI_ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console --instance=1"

SESSION="gz_ardupilot"

GAZEBO_CMD="gz sim -v4 -r \"$WORLD_FILE\""

[ "$VERBOSE" -eq 1 ] && echo "Verbose mode enabled."

cleanup() {
  echo "Cleaning up temporary files..."
  rm -f mav.tlog* mav.tlog.raw mav.parm eeprom.bin
  rm -rf terrain logs
  echo "Cleanup done."
}
trap cleanup EXIT

#tmux has-session -t $SESSION 2>/dev/null && tmux kill-session -t $SESSION

# Kill any old session (ignore errors if it doesn't exist)
tmux kill-session -t $SESSION 2>/dev/null || true

# Start session with gazebo in the first window
tmux new-session -d -s $SESSION "$GAZEBO_CMD"

tmux new-window -t $SESSION -n ardupilot_main "$ARDU_CMD"

tmux new-window -t $SESSION -n ardupilot_sim "$MINI_ARDU_CMD"

# Add mediamtx window if simulation is enabled
if [ "$IS_SIMULATION" = true ]; then
	tmux new-window -t $SESSION -n mediamtx "./mediamtx"
	tmux new-window -t $SESSION -n remote_server "make remote_sim_server_zmq"
	tmux new-window -t $SESSION -n local_server "make local_sim_server_zmq"
fi


# tmux new-window -t $SESSION -n local_server ""

# # Add local_server window
# tmux new-window -t $SESSION:local_server "cd $HOME/Desktop/code/matek && source venv/bin/activate && python3 src/mq/local_server.py"

# Attach to the session
tmux attach-session -t $SESSION
