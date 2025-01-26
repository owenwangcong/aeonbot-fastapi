#!/bin/bash

# Exit on any error
set -e

# Define variables
SERVICE_NAME="aeonbot"
APP_DIR="/home/aeonics/aeonbot-fastapi"
START_SCRIPT="$APP_DIR/start_app.sh"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if start_app.sh exists and is executable
if [ ! -x "$START_SCRIPT" ]; then
    echo "Making start_app.sh executable..."
    chmod +x "$START_SCRIPT"
fi

# Create systemd service file
echo "Creating systemd service file..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Aeonbot Control Application
After=network.target

[Service]
Type=simple
User=aeonics
WorkingDirectory=$APP_DIR
ExecStart=$START_SCRIPT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions for service file
chmod 644 /etc/systemd/system/$SERVICE_NAME.service

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting $SERVICE_NAME service..."
systemctl enable $SERVICE_NAME.service
systemctl start $SERVICE_NAME.service

# Check status
echo "Checking service status..."
systemctl status $SERVICE_NAME.service

echo "Installation complete! The service will now start automatically at boot."
echo "You can check the status anytime with: sudo systemctl status $SERVICE_NAME"
