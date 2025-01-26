#!/usr/bin/env bash
#
# start.sh - Starts FastAPI + Pi Camera app with uvicorn
#

# Exit immediately on error
set -e

PROJECT_DIR="/home/aeonics/aeonbot-fastapi"

# Verify environment
cd "$PROJECT_DIR" || {
    echo "Error: Project directory not found at $PROJECT_DIR" >&2
    exit 1
}

if [ ! -f "main.py" ]; then
    echo "Error: main.py not found in $PROJECT_DIR" >&2
    exit 1
}

# Start uvicorn in the foreground
# This is important for systemd to track the process properly
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
