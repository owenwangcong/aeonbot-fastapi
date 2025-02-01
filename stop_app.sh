#!/usr/bin/env bash
#
# stop_app.sh - Stops FastAPI + Pi Camera app
#

# Exit immediately on error
set -e

PROJECT_DIR="/home/aeonics/aeonbot-fastapi"
PID_FILE="$PROJECT_DIR/uvicorn.pid"

sudo systemctl stop aeonbot.service

echo "=== Server stopped ===" 
