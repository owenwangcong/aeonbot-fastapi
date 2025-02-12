import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRecorder
from fastapi import WebSocket

class WebRTCStream(VideoStreamTrack):
    def __init__(self, camera):
        super().__init__()
        self.camera = camera

    async def recv(self):
        frame = await self.camera.get_frame()
        return frame

class WebRTCManager:
    def __init__(self):
        self.pcs = set()

    async def offer(self, websocket: WebSocket, camera):
        try:
            print("WebSocket connection established")
            pc = RTCPeerConnection()
            self.pcs.add(pc)
            print("PeerConnection created")

            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                print(f"ICE connection state changed to {pc.iceConnectionState}")
                if pc.iceConnectionState == "failed":
                    print("ICE connection failed, closing PeerConnection")
                    await pc.close()
                    self.pcs.discard(pc)

            # Add video track
            video = WebRTCStream(camera)
            pc.addTrack(video)
            print("Video track added")

            # Handle offer
            offer = await websocket.receive_text()
            print("Received offer")
            await pc.setRemoteDescription(RTCSessionDescription(sdp=offer, type="offer"))

            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            print("Created answer")

            # Send answer
            await websocket.send_text(pc.localDescription.sdp)
            print("Sent answer")

        except Exception as e:
            print(f"WebRTC error: {str(e)}")
            await websocket.close()

    async def cleanup(self):
        for pc in self.pcs:
            await pc.close()
        self.pcs.clear() 