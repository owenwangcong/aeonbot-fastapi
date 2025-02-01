import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import time
import sys

def test_pipeline(pipeline_string, timeout=10):
    print(f"\nTesting pipeline: {pipeline_string}")
    try:
        pipeline = Gst.parse_launch(pipeline_string)
        sink = pipeline.get_by_name('sink')
        
        if not sink:
            return False, "Failed to create sink element"
        
        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            return False, "Failed to start pipeline"
        
        # Wait for pipeline to start
        ret = pipeline.get_state(timeout * Gst.SECOND)
        if ret[0] == Gst.StateChangeReturn.SUCCESS:
            print("Pipeline started successfully!")
            time.sleep(2)  # Let it run briefly
            pipeline.set_state(Gst.State.NULL)
            return True, "Success"
        else:
            return False, f"Pipeline failed to start: {ret[0]}"
            
    except Exception as e:
        return False, str(e)
    finally:
        if 'pipeline' in locals():
            pipeline.set_state(Gst.State.NULL)

def main():
    Gst.init(None)
    
    pipelines = [
        # Pipeline 1: Test pattern with tee
        '''videotestsrc ! video/x-raw,width=1280,height=720 ! 
           tee name=t ! queue ! videoconvert ! jpegenc quality=85 ! 
           appsink name=sink emit-signals=true sync=false''',
           
        # Pipeline 2: Test pattern with lower resolution
        '''videotestsrc ! video/x-raw,width=640,height=480 ! 
           videoconvert ! jpegenc quality=85 ! 
           appsink name=sink emit-signals=true sync=false''',
           
        # Pipeline 3: Test pattern with specific format
        '''videotestsrc ! video/x-raw,width=1280,height=720,format=I420 ! 
           videoconvert ! jpegenc quality=85 ! 
           appsink name=sink emit-signals=true sync=false''',
           
        # Pipeline 4: Test pattern with queue settings
        '''videotestsrc ! video/x-raw,width=1280,height=720 ! 
           queue max-size-buffers=1 leaky=downstream ! 
           videoconvert ! jpegenc quality=85 ! 
           appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true''',
           
        # Pipeline 5: Test pattern with framerate
        '''videotestsrc ! video/x-raw,width=1280,height=720,framerate=30/1 ! 
           videoconvert ! jpegenc quality=85 ! 
           appsink name=sink emit-signals=true sync=false'''
    ]
    
    print("Testing GStreamer pipelines...\n")
    
    for i, pipeline in enumerate(pipelines, 1):
        success, message = test_pipeline(pipeline)
        print(f"Pipeline {i}: {'✓ Success' if success else '✗ Failed'} - {message}")
        print("-" * 80)

if __name__ == "__main__":
    main() 