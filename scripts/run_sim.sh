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

error() {
  echo -e "\033[31m$1\033[0m"
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

# Validate world file
if [ -z "$WORLD_FILE" ]; then
  error "Error: World file '$WORLD_FILE' not found."
  usage
fi

IFS=':' read -ra DIRS <<<"$GZ_SIM_RESOURCE_PATH"

FOUND=0

for dir in "${DIRS[@]}"; do
  # Look recursively for the world file
  FILE_PATH=$(find "$dir" -type f -name "$WORLD_FILE" 2>/dev/null | head -n 1)

  if [ -n "$FILE_PATH" ]; then
    echo "Found world file at: $FILE_PATH"
    FOUND=1
    break
  fi
done

if [ "$FOUND" -eq 0 ]; then
  error "Error: World file '$WORLD_FILE' not found. Check the GZ_SIM_RESOURCE_PATH environment variable."
  error "You can set it using \`make set_env_var\`, but please make sure previous variables are removed first."
  exit 1
fi

# Check for required commands
if ! command -v gz >/dev/null 2>&1; then
  error "Error: 'gz' command not found. Please install Gazebo."
  exit 1
fi
if [ ! -f "$HOME/ardupilot/Tools/autotest/sim_vehicle.py" ]; then
  error "Error: 'sim_vehicle.py' not found at $HOME/ardupilot/Tools/autotest/"
  exit 1
fi

# Check /tmp permissions
if [ "$(stat -c %A /tmp)" != "drwxrwxrwt" ]; then
  echo "Fixing /tmp permissions..."
  sudo chmod 1777 /tmp
fi

ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --custom-location=40.9588862,29.1357976,0,0 --model JSON --console --instance=0"
MINI_ARDU_CMD="$HOME/ardupilot/Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --custom-location=40.9588862,29.1357976,0,0 --model JSON --console --instance=1"

# Name of the tmux session
SESSION="gz_ardupilot"

# Build the command
GAZEBO_CMD="gz sim -v4 -r $WORLD_FILE"

[ "$VERBOSE" -eq 1 ] && echo "scoop de pop scoop le poop de poop"

# Cleanup function
cleanup() {
  echo "Cleaning up temporary files..."
  rm -f mav.tlog* mav.tlog.raw mav.parm eeprom.bin
  rm -rf terrain/ logs/
  echo "Cleanup done."
}

# Set the cleanup function to run on exit
trap cleanup EXIT

# Clean up stale tmux socket
rm -f /tmp/tmux-$(id -u)/default

# Kill old session if exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Killing existing session: $SESSION"
  tmux kill-session -t "$SESSION"
  sleep 1
fi

# Start session and name the window
[ "$VERBOSE" -eq 1 ] && echo "Starting tmux session: $SESSION"
(
  tmux new-session -d -s $SESSION -n gazebo
) || {
  echo "Failed to create tmux sessions"
  exit 1
}

tmux new-window -t $SESSION:2 -n ardu_mini
tmux new-window -t $SESSION:3 -n ardu_main

tmux send-keys -t $SESSION:1 "$GAZEBO_CMD" C-m
tmux send-keys -t $SESSION:2 "$MINI_ARDU_CMD" C-m
tmux send-keys -t $SESSION:3 "$ARDU_CMD" C-m

# Layout and attach
tmux attach -t "$SESSION" || {
  echo "Failed to attach to tmux session"
  exit 1
}
