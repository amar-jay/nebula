#!/bin/bash

# Usage info
usage() {
  echo "Usage: $0 [-v] [-w <world_file.sdf>]"
  echo "  -v               scoop de pop scoop le poop de poop"
  echo "  -w <file.sdf>    Specify world file to load"
  echo "Example:"
  echo "  $0 -v -w iris_runway.sdf"
  exit 1
}

# Default: no verbose flag
VERBOSE=0
# world file is the first argument
WORLD_FILE=$1

# Parse CLI options
while getopts ":vw:" opt; do
  case $opt in
  v) VERBOSE=1 ;;
  w) WORLD_FILE="$OPTARG" ;;
  *) usage ;;
  esac
done

ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris  --custom-location=40.95903888690079,29.135350967589982,0,0 --model JSON --console --instance=0" # --instance=1 --out=udp:127.0.0.1:14550"
MINI_ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris  --custom-location=40.9590514,29.1355062,0,0 --model JSON --console --instance=1"           # --instance=1 --out=udp:127.0.0.1:14550"
#MINI_ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console --instance=1"
#ARDU_CMD="sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console"

# Name of the tmux session
SESSION="gz_ardupilot"

# Build the command
GAZEBO_CMD="gz sim -v4 -r"
GAZEBO_CMD="$GAZEBO_CMD $WORLD_FILE"

[ "$VERBOSE" -eq 1 ] && echo "scoop de pop scoop le poop de poop"

# Cleanup function
cleanup() {
  echo "Cleaning up temporary files..."
  # Add file cleanup commands here, for example:
  rm mav.tlog* mav.tlog.raw mav.parm eeprom.bin
  rm -rf terrain/ logs/
  echo "Cleanup done."
}

# Set the cleanup function to run on exit
trap cleanup EXIT

# Kill old session if exists
tmux has-session -t $SESSION 2>/dev/null
if [ $? -eq 0 ]; then
  tmux kill-session -t $SESSION
fi

# Start session and name the window
tmux new-session -d -s $SESSION -n gazebo "$GAZEBO_CMD"
tmux split-window -h -t $SESSION "$ARDU_CMD"

# tmux split-window -v -t $SESSION:.1 "$MINI_ARDU_CMD"

# Rename second pane's window (if ArduPilot tries to rename)
tmux select-pane -t $SESSION:.1
tmux select-window -t $SESSION:0
#tmux rename-window -t $SESSION:0 'Gazebo+ArduPilot'

# Layout and attach
tmux select-layout -t $SESSION tiled
tmux attach-session -t $SESSION
