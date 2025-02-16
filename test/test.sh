#!/bin/sh

# Build the Docker image
cd ..
docker rmi twse-udp-resolver-img
docker build . -t twse-udp-resolver-img
SESSION_NAME="twse-udp-resolver-testing"

# Start a tmux session
tmux new-session -d -s $SESSION_NAME

# Start the parser container
tmux send-keys -t $SESSION_NAME \
    "docker run --rm --name=testing-container twse-udp-resolver-img python3 test/TWSE_mocker.py" C-m

# Create a new pane and start the mocker container
tmux split-window -h -t $SESSION_NAME
tmux send-keys -t $SESSION_NAME \
    "docker exec -it testing-container ./build/twse_udp_resolver_cpp_interface" C-m

# Attach to the tmux session
tmux attach-session -t $SESSION_NAME