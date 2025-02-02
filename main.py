import time
from fastapi import FastAPI, Request, Form
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

# Add a small pydantic model for bounding box coordinates
class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int

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

@app.post("/start-tracking")
async def start_tracking(bbox: BBox):
    """Endpoint to start tracking an object given its bounding box."""
    success = camera.start_tracking(bbox.x, bbox.y, bbox.w, bbox.h)
    if success:
        return JSONResponse({"success": True, "message": "Tracking started."})
    else:
        return JSONResponse({"success": False, "message": "Failed to start tracker."})

@app.post("/reset-tracking")
async def reset_tracking():
    """Endpoint to reset the tracker (stop tracking)."""
    camera.reset_tracking()
    return JSONResponse({"success": True, "message": "Tracker reset."})

@app.post("/set_pipeline_settings")
async def set_pipeline_settings(
    color_format: str = Form(None),
    jpeg_quality: str = Form(None)
):
    # Convert jpeg_quality to int if provided
    if jpeg_quality is not None:
        jpeg_quality = int(jpeg_quality)
    
    # Pass as keyword arguments
    camera.set_pipeline_settings(color_format=color_format, jpeg_quality=jpeg_quality)
    
    # Return a response (FastAPI doesn't use Flask's redirect)
    return {"success": True}
