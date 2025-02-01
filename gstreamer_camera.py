import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import threading
import time
import sys
import queue

class GStreamerCamera:
    def __init__(self):
        Gst.init(None)
        
        print("Initializing GStreamer Camera...")
        
        # Create a queue for frames
        self.frame_queue = queue.Queue(maxsize=10)
        
        self.current_width = 1280
        self.current_height = 720
        self.pipeline = None
        self.create_pipeline()

        # Add telemetry tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0
        self.pipeline_status = "Initializing"
        self.resolution = "1280x720"
        self.frame_format = "JPEG"

    def create_pipeline(self):
        # Stop existing pipeline if it exists
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        # Create new pipeline with current resolution
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
            
            # Connect to the new-sample signal
            self.sink.connect("new-sample", self._new_sample)
            
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            
            # Start pipeline
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

    def _new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample:
            # Update frame count and FPS calculation
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= 1.0:  # Update FPS every second
                self.current_fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.start_time = time.time()

            buffer = sample.get_buffer()
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                # Convert memoryview to bytes
                data = bytes(map_info.data)
                buffer.unmap(map_info)
                try:
                    # Put the frame in the queue, drop if queue is full
                    self.frame_queue.put_nowait(data)
                except queue.Full:
                    pass  # Drop frame if queue is full
        return Gst.FlowReturn.OK

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

    def generate_frames(self):
        print("Starting frame generation...")
        frame_count = 0
        last_time = time.time()
        
        while True:
            try:
                # Get frame from queue with timeout
                data = self.frame_queue.get(timeout=5)
                
                # Calculate and print FPS every 30 frames
                frame_count += 1
                if frame_count % 30 == 0:
                    current_time = time.time()
                    fps = 30 / (current_time - last_time)
                    print(f"FPS: {fps:.2f}")
                    last_time = current_time
                
                # Construct the multipart response
                frame = b'--frame\r\n' + \
                       b'Content-Type: image/jpeg\r\n\r\n' + \
                       data + \
                       b'\r\n'
                yield frame
                
            except queue.Empty:
                print("No frames available", file=sys.stderr)
                time.sleep(0.1)
                continue
            except Exception as e:
                print(f"Error in generate_frames: {e}", file=sys.stderr)
                time.sleep(0.1)
                continue

    def get_telemetry(self):
        return {
            "fps": f"{self.current_fps:.1f}",
            "status": self.pipeline_status,
            "resolution": f"{self.current_width}x{self.current_height}",
            "format": self.frame_format
        }

    def __del__(self):
        print("Cleaning up camera resources...")
        self.running = False
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL) 