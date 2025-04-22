#!/bin/bash
touch /tmp/agent-heartbeat

# Update the heartbeat every 30s
while true; do
    echo "$(date)" > /tmp/agent-heartbeat
    sleep 30 &
    prefect worker start --pool "$WORK_POOL" &
    wait -n
done
