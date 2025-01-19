#!/usr/bin/env bash
#
# start.sh - Starts FastAPI + Pi Camera app with uvicorn from /home/aeonics/fastapi_camera_app
#

# Exit immediately on error
set -e

PROJECT_DIR="/home/aeonics/aeonbot-fastapi"
LOG_FILE="$PROJECT_DIR/uvicorn.log"
PID_FILE="$PROJECT_DIR/uvicorn.pid"

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
sudo echo $! > "$PID_FILE"
echo "Uvicorn server started in background with PID $(cat "$PID_FILE")."
echo "Logs are being written to $LOG_FILE."
