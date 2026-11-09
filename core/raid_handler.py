import logging

from uart.protocol import Command, Frame
from uart.serial_link import SerialLink

from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from camera.capture import CameraCapture
    from network.ws_client import WebSocketClient
from base64 import b64encode
import cv2

logger = logging.getLogger(__name__)

COMMAND_MAP: dict[str, Command] = {
    "move": Command.MOVE,
    "stop": Command.STOP,
    "set_gait": Command.SET_GAIT,
    "set_pose": Command.SET_POSE,
    "telemetry": Command.REQUEST_TELEMETRY,
    "set_led": Command.SET_LED,
    "home": Command.HOME
}


class RaidHandler:
    def __init__(self, serial_link: SerialLink):
        self._serial = serial_link

    async def handle_server_command(self, message: dict[str, Any]) -> None:
        action = message.get("action", "")
        params = message.get("params", {})
        command = COMMAND_MAP.get(action)

        if command is None:
            logger.warning("unknown command action: %s", action)
            return

        payload = self._encode_params(command, params)
        frame = Frame(command, payload)
        await self._serial.send(frame)

        logger.info("sent UART command: %s", action)

    @staticmethod
    def _encode_params(command: Command, params: dict[str, Any]) -> bytes:
        if command == Command.MOVE:
            vx = int(params.get("vx", 0)) & 0xFF
            vy = int(params.get("vy", 0)) & 0xFF
            vr = int(params.get("vr", 0)) & 0xFF
            return bytes([vx, vy, vr])
        if command == Command.SET_GAIT:
            gait_id = int(params.get("gait_id", 0)) & 0xFF
            return bytes([gait_id])
        if command == Command.SET_POSE:
            roll = int(params.get("roll", 0)) & 0xFF
            pitch = int(params.get("pitch", 0)) & 0xFF
            yaw = int(params.get("yaw", 0)) & 0xFF
            return bytes([roll, pitch, yaw])
        if command == Command.SET_LED:
            state = int(params.get("state", 0)) & 0xFF
            return bytes([state])
        return b""

    @staticmethod
    def photo_request_handler_factory(camera_link: "CameraCapture", ws_client: "WebSocketClient"):
        async def photo_request_handler(message: dict[str, Any]) -> None:
            frame = await camera_link.get_frame()
            if frame is None:
                logger.warning("camera frame capture failed")
                await ws_client.send_message("photo_response", {
                    "status": "error",
                    "detail": "failed to capture frame from camera"
                })
                return

            success, encoded_img = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not success:
                logger.warning("JPEG encoding failed")
                return
            photo_b64 = b64encode(encoded_img.tobytes()).decode("utf-8")
            await ws_client.send_message("photo_response", {
                "image": photo_b64,
                "format": "jpeg"
            })
            logger.info("captured and dispatched photo response")
        return photo_request_handler
