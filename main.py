import time
import cv2
from picamera2 import Picamera2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse

app = FastAPI()

# Initialize and start camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (1640, 1480)})
picam2.configure(config)
picam2.start()
time.sleep(2)

def generate_frames():
    while True:
        frame = picam2.capture_array()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ret, buffer = cv2.imencode('.jpg', frame_rgb)
        if not ret:
            continue
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.get("/", response_class=HTMLResponse)
def root():
    # Embed the stream on the main page.
    return """
    <html>
    <head><title>Raspberry Pi Camera Stream</title></head>
    <body>
    <h1>Raspberry Pi Camera v3 Streaming</h1>
    <img src="/video-feed" width="640" height="480" />
    </body>
    </html>
    """

@app.get("/video-feed")
def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )
