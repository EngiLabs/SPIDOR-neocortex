import logging
from typing import Any

from uart.protocol import Command, Frame
from uart.serial_link import SerialLink

logger = logging.getLogger(__name__)

COMMAND_MAP: dict[str, Command] = {
    "move": Command.MOVE,
    "stop": Command.STOP,
    "set_gait": Command.SET_GAIT,
    "set_pose": Command.SET_POSE,
    "request_telemetry": Command.REQUEST_TELEMETRY,
    "set_led": Command.SET_LED,
    "home": Command.HOME,
}


class RaidHandler:
    def __init__(self, serial_link: SerialLink):
        self._serial = serial_link

    async def handle_server_command(self, message: dict[str, Any]) -> None:
        action = message.get("action", "")
        params = message.get("params", {})
        command = COMMAND_MAP.get(action)
        if command is None:
            logger.warning("Unknown command action: %s", action)
            return
        payload = self._encode_params(command, params)
        frame = Frame(command, payload)
        await self._serial.send(frame)
        logger.info("Sent UART command: %s", action)

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
