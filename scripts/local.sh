#!/bin/bash

SESSION="local"

if tmux has-session -t $SESSION 2>/dev/null; then
		echo "Session $SESSION already exists. Attaching..."
		tmux attach -t $SESSION
		exit 0
fi

# Start a new tmux session, detached
tmux new-session -d -s $SESSION -n system

tmux new-window -t $SESSION:2 -n USB0

tmux new-window -t $SESSION:3 -n USB1
# tmux new-window -t $SESSION:3 -n gpu

tmux new-window -t $SESSION:4 -n local_server

tmux new-window -t $SESSION:5 -n app

# Pre-fill a command in window1 without executing
tmux send-keys -t $SESSION:1 "btop" C-m 

# Pre-fill a command in window2 without executing
tmux send-keys -t $SESSION:2 "mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --console --out=udp:127.0.0.1:14560"  # <-- no Enter here

# Pre-fill a command in window3 without executing
tmux send-keys -t $SESSION:3 "mavproxy.py --master=/dev/ttyUSB1 --baudrate=57600 --out=udp:127.0.0.1:14570"  # <-- no Enter here
# tmux send-keys -t $SESSION:3 "nvtop" C-m  # <-- no Enter here

# Pre-fill a command in window4 without executing
tmux send-keys -t $SESSION:4 "make local_server"  # <-- no Enter here

# Pre-fill a command in window5 without executing
tmux send-keys -t $SESSION:5 "make app"  # <-- no Enter here


# Attach to the session
tmux attach -t $SESSION
