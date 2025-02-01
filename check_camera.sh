#!/bin/bash

echo "Checking video devices..."
ls -l /dev/video*

echo -e "\nChecking v4l2 devices..."
v4l2-ctl --list-devices

echo -e "\nChecking default video device capabilities..."
v4l2-ctl --device=/dev/video0 --all 