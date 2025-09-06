#!/bin/bash

SESSION="remote"

if tmux has-session -t $SESSION 2>/dev/null; then
		echo "Session $SESSION already exists. Attaching..."
		tmux attach -t $SESSION
		exit 0
fi

# Start a new tmux session, detached
tmux new-session -d -s $SESSION -n telem

# Create the second window
tmux new-window -t $SESSION:2 -n top

# Create the second window
tmux new-window -t $SESSION:3 -n server

# Pre-fill a command in window1 without executing
tmux send-keys -t $SESSION:1 "mavproxy.py --master=/dev/ttyACM0 --baudrate=57600 --console --out=udp:0.0.0.0:14550"  # <-- no Enter here

# Pre-fill a command in window2 without executing
tmux send-keys -t $SESSION:2 "top" C-m  # <-- no Enter here

# Pre-fill a command in window2 without executing
tmux send-keys -t $SESSION:3 "make remote_server"  # <-- no Enter here

# Attach to the session
tmux attach -t $SESSION
