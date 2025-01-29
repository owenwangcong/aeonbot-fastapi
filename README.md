# Raspberry Pi Camera Streaming Server

A FastAPI-based web server that streams video from a Raspberry Pi Camera v3 module. The stream can be viewed through any web browser.

## Requirements

- Raspberry Pi (tested on Raspberry Pi 4)
- Raspberry Pi Camera v3
- Python 3.7+
- Required Python packages:
  - fastapi
  - uvicorn
  - opencv-python
  - picamera2

## Installation

## Commands

### Copy file to Raspberry Pi
scp -rp ./* aeonics@10.0.0.101:/home/aeonics/aeonbot-fastapi/