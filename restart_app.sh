#!/usr/bin/env bash
#
# restart_app.sh - Restarts FastAPI + Pi Camera app with uvicorn
#

# Exit immediately on error
set -e

PROJECT_DIR="/home/aeonics/aeonbot-fastapi"
LOG_FILE="$PROJECT_DIR/uvicorn.log"
PID_FILE="$PROJECT_DIR/uvicorn.pid"

echo "=== Checking for running instance ==="
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null; then
        echo "Stopping existing process (PID: $OLD_PID)"
        sudo kill "$OLD_PID"
        sleep 2  # Wait for process to stop
    else
        echo "No running process found with PID: $OLD_PID"
    fi
    sudo rm -f "$PID_FILE"
fi

echo "=== Navigating to $PROJECT_DIR ==="
cd "$PROJECT_DIR" || {
    echo "Project directory not found at $PROJECT_DIR"
    exit 1
}

if [ ! -f "main.py" ]; then
    echo "Error: main.py not found in $PROJECT_DIR"
    exit 1
fi

echo "=== Starting FastAPI server with uvicorn in background ==="
# Run uvicorn in the background via nohup, output logs to uvicorn.log
sudo nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &

# Store the process ID
echo $! > "$PID_FILE"
echo "Uvicorn server restarted in background with PID $(cat "$PID_FILE")."
echo "Logs are being written to $LOG_FILE." 