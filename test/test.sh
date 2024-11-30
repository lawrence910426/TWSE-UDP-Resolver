#!/bin/sh
# Spawn two Dockers, one for the parser and the another one sends example UDP packets to the parser.

cd ..
docker build . -t twse-udp-resolver-img

SESSION_NAME="twse-udp-resolver-testing"
tmux new-session -d -s $SESSION_NAME
tmux send-keys -t $SESSION_NAME "docker run twse-udp-resolver-img" C-m
tmux split-window -h -t $SESSION_NAME
tmux send-keys -t $SESSION_NAME "docker run twse-udp-resolver-img python3 test/TWSE_mocker.py" C-m
tmux attach-session -t $SESSION_NAME
