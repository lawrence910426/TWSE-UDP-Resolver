#!/bin/sh
# Spawn two Dockers, one for the parser and the another one sends example UDP packets to the parser.
#!/bin/sh
# Spawn two Dockers, one for the parser and the other for sending example UDP packets.

# Build the Docker image
cd ..
docker rm twse-udp-resolver-img
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
    "docker exec -it testing-container ./build/main" C-m

# Attach to the tmux session
tmux attach-session -t $SESSION_NAME