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

        # Keep track of color format, JPEG quality, and encoder for the pipeline
        self.color_format = "RGBx"
        self.jpeg_quality = 85
        self.current_encoder = "jpegenc"  # Default encoder
        
        # Get supported encoders
        self.supported_encoders = self._get_supported_encoders()
        print("Supported encoders:", self.supported_encoders)

        # Instead, just store a static list of common resolutions:
        self.supported_resolutions = self._get_supported_resolutions()
        print("Supported resolutions:", self.supported_resolutions)

        # Get supported formats and resolutions
        self.supported_formats = self._get_supported_formats()
        print("Supported formats:", self.supported_formats)

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

    def _get_supported_formats(self):
        """
        Get list of supported color formats from GStreamer.
        """
        try:
            # Create a test source to query formats
            caps = Gst.Caps.from_string("video/x-raw")
            formats = []
            
            # Common formats to test
            test_formats = [
                "RGB", "BGR", "RGBx", "BGRx", "xRGB", "xBGR",
                "RGBA", "BGRA", "ARGB", "ABGR", "GREY", "GRAY", "GRAY8", "GRAY16_LE",
                "GRAY16_BE", "YUY2", "UYVY", "YVYU", "I420", "YV12",
                "NV12", "NV21"
            ]
            
            for fmt in test_formats:
                test_caps = Gst.Caps.from_string(f"video/x-raw,format={fmt}")
                if test_caps.is_fixed():
                    formats.append(fmt)
            
            if not formats:
                # Fallback to basic formats if none found
                formats = ["RGBx", "GRAY8", "NV12", "YUY2"]
                
            print("Supported formats:", formats)
            return formats
            
        except Exception as e:
            print(f"Error getting supported formats: {e}", file=sys.stderr)
            # Return basic formats as fallback
            return ["RGBx", "GRAY8", "NV12", "YUY2"]

    def _get_supported_encoders(self):
        """
        Query GStreamer for available video encoders and return a dict of encoder info.
        """
        encoders = {}
        
        # List of common video encoders to check
        encoder_elements = [
            ("jpegenc", "JPEG", "image/jpeg"),
            ("x264enc", "H.264", "video/x-h264"),
            ("vp8enc", "VP8", "video/x-vp8"),
            ("vp9enc", "VP9", "video/x-vp9"),
            ("av1enc", "AV1", "video/x-av1"),
            ("mpeg2enc", "MPEG2", "video/mpeg")
        ]
        
        for element_name, friendly_name, mime_type in encoder_elements:
            element = Gst.ElementFactory.find(element_name)
            if element:
                encoders[element_name] = {
                    "name": friendly_name,
                    "mime_type": mime_type,
                    "element": element_name
                }
        
        if not encoders:
            # Fallback to just JPEG if no encoders found
            encoders["jpegenc"] = {
                "name": "JPEG",
                "mime_type": "image/jpeg",
                "element": "jpegenc"
            }
        
        return encoders

    def set_pipeline_settings(self, color_format=None, jpeg_quality=None, encoder=None):
        """
        Dynamically update pipeline settings such as color format, quality, and encoder,
        then recreate the pipeline to apply changes.
        """
        if color_format is not None:
            self.color_format = color_format
        if jpeg_quality is not None:
            self.jpeg_quality = jpeg_quality
        if encoder is not None and encoder in self.supported_encoders:
            self.current_encoder = encoder

        # Re-create the pipeline with the updated settings
        self.create_pipeline()

    def create_pipeline(self):
        # If pipeline exists, stop it
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        # Configure encoder element based on selected encoder
        encoder_config = ""
        decoder_config = ""
        if self.current_encoder == "jpegenc":
            encoder_config = f"jpegenc quality={self.jpeg_quality}"
        elif self.current_encoder == "x264enc":
            encoder_config = "x264enc tune=zerolatency speed-preset=ultrafast"
            decoder_config = "! h264parse ! avdec_h264 ! jpegenc quality=85"
        elif self.current_encoder == "vp8enc":
            encoder_config = "vp8enc deadline=1"
            decoder_config = "! vp8dec ! jpegenc quality=85"
        elif self.current_encoder == "vp9enc":
            encoder_config = "vp9enc deadline=1"
            decoder_config = "! vp9dec ! jpegenc quality=85"
        else:
            # Default fallback to the encoder name if no special config needed
            encoder_config = self.current_encoder

        # Update pipeline string with dynamic encoder and decoder
        self.pipeline_string = (
            f'libcamerasrc ! '
            f'video/x-raw,format={self.color_format},width={self.current_width},height={self.current_height},framerate=30/1 ! '
            f'videoconvert ! {encoder_config} {decoder_config} ! '
            f'appsink name=sink emit-signals=true sync=false'
        )

        try:
            print(f"Creating pipeline: {self.pipeline_string}")  # Debug print
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

            # Create and initialize the tracker
            self.tracker = self.get_tracker()
            if self.tracker is None:
                print("No suitable tracker available", file=sys.stderr)
                return False

            self.tracker.init(frame_cv, (x, y, w, h))
            self.tracked_bbox = (x, y, w, h)
            self.tracking_active = True
            print(f"{type(self.tracker).__name__} tracker initialized with bbox:", self.tracked_bbox)
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
        """Get camera telemetry data."""
        telemetry = {
            "fps": f"{self.current_fps:.1f}",
            "status": self.pipeline_status,
            "resolution": f"{self.current_width}x{self.current_height}",
            "format": self.frame_format,
            "supported_resolutions": [f"{w}x{h}" for w, h in self.supported_resolutions],
            "supported_formats": self.supported_formats,
            "current_encoder": self.current_encoder,
            "supported_encoders": self.supported_encoders
        }
        return telemetry

    def get_tracker(self):
        try:
            # Try CSRT first (most accurate)
            return cv2.TrackerCSRT_create()
        except AttributeError:
            try:
                # Fall back to MOSSE if CSRT isn't available
                return cv2.TrackerMOSSE_create()
            except AttributeError:
                try:
                    # Fall back to KCF if MOSSE isn't available
                    return cv2.TrackerKCF_create()
                except AttributeError:
                    try:
                        # Fall back to Boosting if KCF isn't available
                        return cv2.TrackerBoosting_create()
                    except AttributeError:
                        try:
                            # Fall back to MIL if Boosting isn't available
                            return cv2.TrackerMIL_create()
                        except AttributeError:
                            print("No suitable tracker available in this OpenCV version", file=sys.stderr)
                            return None

    def __del__(self):
        print("Cleaning up camera resources...")
        self.running = False
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL) 