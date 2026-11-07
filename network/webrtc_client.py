import logging
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

from ..config import CAMERA_HEIGHT, CAMERA_WIDTH


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from camera.capture import CameraCapture
    from network.ws_client import WebSocketClient

logger = logging.getLogger(__name__)


class CameraStreamTrack(VideoStreamTrack):
    def __init__(self, camera: "CameraCapture"):
        super().__init__()
        self._camera = camera

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame_data = await self._camera.get_frame()
        if frame_data is None:
            frame_data = np.zeros((CAMERA_WIDTH, CAMERA_HEIGHT, 3), dtype=np.uint8)
        video_frame = VideoFrame.from_ndarray(frame_data, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame


class WebRTCClient:
    def __init__(self, camera: "CameraCapture", ws_client: "WebSocketClient"):
        self._camera = camera
        self._ws_client = ws_client
        self._pc: RTCPeerConnection | None = None

    async def setup(self) -> None:
        self._ws_client.on("webrtc_answer", self._handle_answer)
        self._ws_client.on("webrtc_ice", self._handle_ice_candidate)

    async def start_offer(self) -> None:
        self._pc = RTCPeerConnection()
        track = CameraStreamTrack(self._camera)
        self._pc.addTrack(track)

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)

        await self._ws_client.send_message("webrtc_offer", {
            "sdp": self._pc.localDescription.sdp,
            "sdp_type": self._pc.localDescription.type,
        })
        logger.info("WRTC offer sent")

    async def _handle_answer(self, message: dict) -> None:
        if self._pc is None:
            return
        answer = RTCSessionDescription(sdp=message["sdp"], type=message["sdp_type"])
        await self._pc.setRemoteDescription(answer)
        logger.info("WRTC answer received")

    async def _handle_ice_candidate(self, message: dict) -> None:
        if self._pc is None:
            return
        candidate = message.get("candidate")
        if candidate:
            await self._pc.addIceCandidate(candidate)

    async def stop(self) -> None:
        if self._pc:
            await self._pc.close()
            self._pc = None
        logger.info("WRTC stopped")
