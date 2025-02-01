#!/bin/bash

# Exit on any error
set -e

echo "Setting up Raspberry Pi Camera Module 3..."

# Add current user to video and gpio groups
sudo usermod -a -G video,gpio $USER

# Create camera config file with more conservative settings
sudo tee /etc/libcamera/camera.conf << EOF
{
    "cameras": [
        {
            "auto_exposure": true,
            "auto_white_balance": true,
            "brightness": 0.0,
            "contrast": 1.0,
            "exposure_time": 33333,
            "gain": 1.0,
            "saturation": 1.0
        }
    ]
}
EOF

# Create udev rules for camera
sudo tee /etc/udev/rules.d/99-camera.rules << EOF
SUBSYSTEM=="video4linux", GROUP="video", MODE="0660"
SUBSYSTEM=="media", GROUP="video", MODE="0660"
SUBSYSTEM=="vchiq", GROUP="video", MODE="0660"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Test camera access
echo "Testing camera access..."
if ! libcamera-hello --list-cameras; then
    echo "Error: Camera not detected!"
    exit 1
fi

# Enable camera in config.txt if not already enabled
if ! grep -q "^camera_auto_detect=1" /boot/config.txt; then
    echo "Enabling camera in config.txt..."
    sudo sh -c 'echo "camera_auto_detect=1" >> /boot/config.txt'
fi

# Test camera capture
echo "Testing camera capture..."
if libcamera-jpeg -o test.jpg; then
    echo "Camera capture test successful!"
    rm test.jpg
else
    echo "Camera capture test failed!"
    exit 1
fi

echo "Camera setup complete. Please reboot for changes to take effect." 