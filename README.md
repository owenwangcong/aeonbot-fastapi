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


### For gstreamer
sudo apt install -y libgstreamer1.0-dev     libgstreamer-plugins-base1.0-dev     libgstreamer-plugins-bad1.0-dev     gstreamer1.0-plugins-base     gstreamer1.0-plugins-good     gstreamer1.0-plugins-bad     gstreamer1.0-plugins-ugly     gstreamer1.0-libav     gstreamer1.0-tools     gstreamer1.0-x     gstreamer1.0-gl     gstreamer1.0-gtk3     gstreamer1.0-qt5     gstreamer1.0-pulseaudio     gstreamer1.0-nice

### Copy file to Raspberry Pi
for %f in (*.sh) do powershell -Command "(Get-Content \"%f\") -replace '`r`n', '`n' | Set-Content \"%f\""
scp -rp ./* aeonics@10.0.0.101:/home/aeonics/aeonbot-fastapi/

#### Then on rp5
chmod +x *.sh | dos2unix *.sh