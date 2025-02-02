# Comment out or remove the Picamera2 import:
# from picamera2 import Picamera2

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import threading
import time
import sys
import queue
import cv2
import numpy as np

class GStreamerCamera:
    # Remove any _global_picam2 references
    # _global_picam2 = None  # (delete this)

    def __init__(self):
        Gst.init(None)

        # Delete code that initializes Picamera2
        # if not GStreamerCamera._global_picam2:
        #     GStreamerCamera._global_picam2 = Picamera2()
        # self.picam2 = GStreamerCamera._global_picam2

        # Instead, just store a static list of common resolutions:
        self.supported_resolutions = self._get_supported_resolutions()
        print("Supported resolutions:", self.supported_resolutions)

        print("Initializing GStreamer Camera...")

        self.frame_queue = queue.Queue(maxsize=10)

        self.current_width = 1280
        self.current_height = 720
        self.pipeline = None
        self.create_pipeline()

        # Telemetry
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0
        self.pipeline_status = "Initializing"
        self.resolution = "1280x720"
        self.frame_format = "JPEG"

        # Tracking
        self.tracker = None
        self.tracking_active = False
        self.tracked_bbox = (0, 0, 0, 0)

    def _get_supported_resolutions(self):
        """
        Return a static list of common resolutions.
        Using libcamerasrc for capture, so no direct Picamera2.
        """
        return [
            (640, 480),    # VGA
            (1280, 720),   # HD
            (1920, 1080),  # Full HD
        ]

    def create_pipeline(self):
        # If pipeline exists, stop it
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        # We'll keep using libcamerasrc in the pipeline
        self.pipeline_string = (
            f'libcamerasrc ! '
            f'video/x-raw,format=RGBx,width={self.current_width},height={self.current_height},framerate=30/1 ! '
            f'videoconvert ! jpegenc quality=85 ! '
            f'appsink name=sink emit-signals=true sync=false'
        )

        try:
            self.pipeline = Gst.parse_launch(self.pipeline_string)
            self.sink = self.pipeline.get_by_name('sink')
            if not self.sink:
                raise Exception("Failed to create sink element")

            self.sink.connect("new-sample", self._new_sample)
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()

            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise Exception("Failed to start pipeline")

            # Wait for pipeline to start
            ret = self.pipeline.get_state(5 * Gst.SECOND)
            if ret[0] != Gst.StateChangeReturn.SUCCESS:
                raise Exception("Pipeline failed to start")

            return True

        except Exception as e:
            print(f"Pipeline creation failed: {e}", file=sys.stderr)
            return False

    def _new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample:
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= 1.0:
                self.current_fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.start_time = time.time()

            buffer = sample.get_buffer()
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                data = bytes(map_info.data)
                buffer.unmap(map_info)
                try:
                    self.frame_queue.put_nowait(data)
                except queue.Full:
                    pass
        return Gst.FlowReturn.OK

    def generate_frames(self):
        print("Starting frame generation...")
        while True:
            try:
                data = self.frame_queue.get(timeout=5)
                frame_cv = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

                # If tracking is active, always draw the bounding box in green
                if self.tracking_active and self.tracker is not None:
                    success, box = self.tracker.update(frame_cv)
                    if success:
                        (x, y, w, h) = [int(v) for v in box]
                        self.tracked_bbox = (x, y, w, h)
                    else:
                        cv2.putText(frame_cv, "Tracking lost", (20, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Always draw the last known tracked_bbox in green
                (bx, by, bw, bh) = self.tracked_bbox
                cv2.rectangle(frame_cv, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame_cv)
                if not ret:
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )

            except queue.Empty:
                time.sleep(0.1)
                continue
            except Exception as e:
                print(f"Error in generate_frames: {e}", file=sys.stderr)
                time.sleep(0.1)
                continue

    def set_resolution(self, width: int, height: int):
        """Change the camera resolution."""
        try:
            # Store new resolution
            self.current_width = width
            self.current_height = height
            
            # Recreate pipeline with new resolution
            success = self.create_pipeline()
            
            if success:
                # Update telemetry
                self.resolution = f"{width}x{height}"
                return True
            return False
            
        except Exception as e:
            print(f"Failed to set resolution: {e}", file=sys.stderr)
            return False

    def _bus_monitor(self):
        while self.running:
            try:
                message = self.bus.timed_pop_filtered(
                    1000000000,  # 1 second timeout
                    Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.STATE_CHANGED | 
                    Gst.MessageType.WARNING
                )
                
                if message:
                    if message.type == Gst.MessageType.ERROR:
                        err, debug = message.parse_error()
                        print(f"GStreamer Error: {err}", file=sys.stderr)
                        print(f"Debug details: {debug}", file=sys.stderr)
                        self.pipeline.set_state(Gst.State.NULL)
                        break
                    elif message.type == Gst.MessageType.WARNING:
                        warn, debug = message.parse_warning()
                        print(f"GStreamer Warning: {warn}", file=sys.stderr)
                        print(f"Debug details: {debug}", file=sys.stderr)
                    elif message.type == Gst.MessageType.EOS:
                        print("End of stream")
                        self.pipeline.set_state(Gst.State.NULL)
                        break
                    elif message.type == Gst.MessageType.STATE_CHANGED:
                        if message.src == self.pipeline:
                            old_state, new_state, pending_state = message.parse_state_changed()
                            print(f"Pipeline state changed from {old_state.value_nick} to {new_state.value_nick}")
            except Exception as e:
                print(f"Error in bus monitor: {e}", file=sys.stderr)

    def start_tracking(self, x: int, y: int, w: int, h: int) -> bool:
        """Initialize the CSRT tracker with the given bounding box."""
        try:
            # Wait up to 1 second for a frame if the queue is empty
            initial_frame = None
            for _ in range(10):  # 10 retries x 0.1s = 1 second
                if not self.frame_queue.empty():
                    initial_frame = self.frame_queue.get_nowait()
                    break
                else:
                    time.sleep(0.1)

            # If still no frame, bail
            if initial_frame is None:
                print("No frame available to start tracking.", file=sys.stderr)
                return False
            
            # Convert raw bytes to a proper image (OpenCV)
            nparr = np.frombuffer(initial_frame, np.uint8)
            frame_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Create and initialize the CSRT tracker
            self.tracker = cv2.legacy.TrackerCSRT_create()
            self.tracker.init(frame_cv, (x, y, w, h))

            self.tracked_bbox = (x, y, w, h)
            self.tracking_active = True
            print("CSRT tracker initialized with bbox:", self.tracked_bbox)
            return True
        except Exception as e:
            print(f"Error starting tracker: {e}", file=sys.stderr)
            return False

    def reset_tracking(self):
        """Reset the tracker."""
        self.tracker = None
        self.tracking_active = False
        self.tracked_bbox = (0, 0, 0, 0)
        print("Tracking has been reset.")

    def get_telemetry(self):
        """Get camera telemetry including supported resolutions."""
        telemetry = {
            "fps": f"{self.current_fps:.1f}",
            "status": self.pipeline_status,
            "resolution": f"{self.current_width}x{self.current_height}",
            "format": self.frame_format,
            "supported_resolutions": [f"{w}x{h}" for w, h in self.supported_resolutions]
        }
        return telemetry

    def __del__(self):
        print("Cleaning up camera resources...")
        self.running = False
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL) 