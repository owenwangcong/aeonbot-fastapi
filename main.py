import time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gstreamer_camera import GStreamerCamera

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize camera
camera = GStreamerCamera()

class ResolutionRequest(BaseModel):
    resolution: str

@app.get("/")
def root(request: Request):
    # Render the template with request context
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/mqtt")
def mqtt_page(request: Request):
    return templates.TemplateResponse("mqtt.html", {"request": request})

@app.get("/motor")
def motor_page(request: Request):
    return templates.TemplateResponse("motor.html", {"request": request})

@app.get("/video-feed")
def video_feed():
    return StreamingResponse(
        camera.generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.get("/camera-telemetry")
async def camera_telemetry():
    return camera.get_telemetry()

@app.post("/set-resolution")
async def set_resolution(request: ResolutionRequest):
    try:
        # Parse the resolution string
        width, height = map(int, request.resolution.split('x'))
        
        # Check if resolution is supported
        if (width, height) not in camera.supported_resolutions:
            return JSONResponse({
                "success": False,
                "error": f"Unsupported resolution: {width}x{height}"
            })
        
        # Attempt to change the camera resolution
        success = camera.set_resolution(width, height)
        
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to set resolution"
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })
