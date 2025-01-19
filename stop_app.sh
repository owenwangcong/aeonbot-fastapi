#!/usr/bin/env bash
#
# stop_app.sh - Stops FastAPI + Pi Camera app
#

# Exit immediately on error
set -e

PROJECT_DIR="/home/aeonics/aeonbot-fastapi"
PID_FILE="$PROJECT_DIR/uvicorn.pid"

echo "=== Checking for running instance ==="
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null; then
        echo "Stopping process with PID: $OLD_PID"
        sudo kill "$OLD_PID"
        sleep 2  # Wait for process to stop
        echo "Process stopped successfully"
    else
        echo "No running process found with PID: $OLD_PID"
    fi
    sudo rm -f "$PID_FILE"
else
    echo "No PID file found at $PID_FILE"
fi

echo "=== Server stopped ===" 