SESSION="gz_ardupilot"

# Kill old session if it exists (don’t complain if none exists)
tmux kill-session -t $SESSION 2>/dev/null || true

# Start session with gazebo
tmux new-session -d -s $SESSION -n gazebo "$GAZEBO_CMD" || {
  echo "Failed to create tmux session"
  exit 1
}

# Split: add ardupilot0 on the right
tmux split-window -h -t $SESSION:gazebo "$ARDU_CMD"

# Split: add ardupilot1 below the right pane
tmux split-window -v -t $SESSION:gazebo.right "$MINI_ARDU_CMD"

# Arrange them nicely
tmux select-layout -t $SESSION:gazebo tiled

# Create mediamtx window (if simulation flag set)
if [ "$IS_SIMULATION" = true ]; then
  tmux new-window -t $SESSION -n mediamtx "mediamtx"
fi

# Create local_server window
tmux new-window -t $SESSION -n local_server \
  "cd $HOME/Desktop/code/matek && source venv/bin/activate && python3 src/mq/local_server.py"

# Finally, attach
tmux attach -t $SESSION
