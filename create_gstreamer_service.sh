#!/bin/bash

sudo tee /etc/systemd/system/gstreamer-permissions.service << EOF
[Unit]
Description=Set up GStreamer permissions
Before=aeonbot.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'chmod a+rw /dev/video* && chmod a+rw /dev/media* && usermod -a -G video aeonics'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo chmod +x /etc/systemd/system/gstreamer-permissions.service
sudo systemctl daemon-reload
sudo systemctl enable gstreamer-permissions.service
sudo systemctl start gstreamer-permissions.service 
