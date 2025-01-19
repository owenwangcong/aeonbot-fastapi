import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

from camera import Camera

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize camera
camera = Camera()

@app.get("/")
def root(request: Request):
    # Render the template with request context
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video-feed")
def video_feed():
    return StreamingResponse(
        camera.generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )
