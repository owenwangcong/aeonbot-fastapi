import cv2
from picamera2 import Picamera2
import time

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        
        # Print camera information
        print("Camera Info:")
        print(f"Camera Model: {self.picam2.camera_properties['Model']}")
        print(f"Camera Modes: {self.picam2.sensor_modes}")
        
        # Using a larger resolution (2592x1944 for 5MP)
        config = self.picam2.create_preview_configuration(main={"size": (2592, 1944)})
        self.picam2.configure(config)
        
        # Print configured resolution
        print(f"Configured Resolution: {config['main']['size']}")
        
        self.picam2.start()
        time.sleep(2)  # Wait for camera to initialize

    def generate_frames(self):
        while True:
            frame = self.picam2.capture_array()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ret, buffer = cv2.imencode('.jpg', frame_rgb)
            if not ret:
                continue
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n') 