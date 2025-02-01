#!/bin/bash

# Exit on any error
set -e

echo "=== Setting up HiveMQ Community Edition ==="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Java 17 (HiveMQ requires Java 11 or newer)
echo "Installing Java 17..."
sudo apt-get install -y openjdk-17-jre-headless

# Verify Java installation
java -version

# Create installation directory
echo "Creating HiveMQ directory..."
sudo mkdir -p /opt/hivemq
cd /opt/hivemq

# Download and install HiveMQ
echo "Downloading HiveMQ Community Edition..."
wget https://github.com/hivemq/hivemq-community-edition/releases/download/2024.9/hivemq-ce-2024.9.zip

echo "Extracting HiveMQ..."
sudo unzip hivemq-*.zip
sudo cp -r hivemq-ce-2024.9/* /opt/hivemq/
sudo rm -rf hivemq-ce-2024.9
sudo rm hivemq-*.zip

# Ensure config directory exists and copy config file
echo "Setting up config directory..."
sudo mkdir -p /opt/hivemq/conf
sudo cp /opt/hivemq/hivemq-ce-2024.9/conf/config.xml /opt/hivemq/conf/

# Create hivemq user and set permissions
echo "Setting up HiveMQ user and permissions..."
sudo useradd -r -d /opt/hivemq hivemq || true
sudo chown -R hivemq:hivemq /opt/hivemq

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/hivemq.service << EOF
[Unit]
Description=HiveMQ MQTT Broker
After=network.target

[Service]
Type=simple
User=hivemq
Group=hivemq
Environment=HIVEMQ_HOME=/opt/hivemq/hivemq-ce-2024.9
Environment=HIVEMQ_CONFIG_FOLDER=/opt/hivemq/conf
ExecStart=/opt/hivemq/hivemq-ce-2024.9/bin/run.sh
WorkingDirectory=/opt/hivemq/hivemq-ce-2024.9
StandardOutput=journal
StandardError=journal
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Create HiveMQ configuration
echo "Creating HiveMQ configuration..."
sudo mkdir -p /opt/hivemq/conf
sudo tee /opt/hivemq/conf/config.xml << EOF
<?xml version="1.0"?>
<hivemq xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="hivemq-config.xsd">

    <listeners>
        <tcp-listener>
            <port>1883</port>
            <bind-address>0.0.0.0</bind-address>
        </tcp-listener>
        <websocket-listener>
            <port>8083</port>
            <bind-address>0.0.0.0</bind-address>
            <path>/mqtt</path>
            <subprotocols>
                <subprotocol>mqttv3.1</subprotocol>
                <subprotocol>mqtt</subprotocol>
            </subprotocols>
        </websocket-listener>
    </listeners>

    <security>
        <allow-anonymous>true</allow-anonymous>
    </security>

</hivemq>
EOF

# Set proper permissions for config
sudo chown -R hivemq:hivemq /opt/hivemq/conf

# Enable and start HiveMQ service
echo "Starting HiveMQ service..."
sudo systemctl daemon-reload
sudo systemctl enable hivemq
sudo systemctl start hivemq

# Wait a few seconds for the service to start
sleep 5

# Check service status
echo "Checking HiveMQ service status..."
sudo systemctl status hivemq
ssss
echo "=== Installation Complete ==="
echo "HiveMQ is now running on:"
echo "MQTT port: 1883"
echo "WebSocket port: 8083"
echo ""
echo "You can check the logs with:"
echo "sudo journalctl -u hivemq -f" 
