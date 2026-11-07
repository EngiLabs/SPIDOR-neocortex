import asyncio
import logging
import struct

from uart.protocol import Command, Frame
from uart.serial_link import SerialLink
from network.ws_client import WebSocketClient

logger = logging.getLogger(__name__)


class TelemetryCollector:
    def __init__(self, serial_link: SerialLink, ws_client: WebSocketClient, poll_interval: float = .1):
        self._serial = serial_link
        self._ws = ws_client
        self._poll_interval = poll_interval
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("telemetry collector started")
        while self._running:
            await self._request_telemetry()
            frame = await self._serial.receive()
            if frame:
                telemetry = self._parse_telemetry(frame)
                if telemetry:
                    await self._ws.send_message("telemetry", {"data": telemetry})
            await asyncio.sleep(self._poll_interval)

    async def _request_telemetry(self) -> None:
        await self._serial.send(Frame(Command.REQUEST_TELEMETRY))

    @staticmethod
    def _parse_telemetry(frame: Frame) -> dict | None:
        if len(frame.payload) < 8:
            return None
        try:
            battery_mv = struct.unpack_from("<H", frame.payload, 0)[0]
            # imu_roll = struct.unpack_from("<h", frame.payload, 2)[0] / 100.0
            # imu_pitch = struct.unpack_from("<h", frame.payload, 4)[0] / 100.0
            # imu_yaw = struct.unpack_from("<h", frame.payload, 6)[0] / 100.0
            return {
                "battery_mv": battery_mv,
                # "imu_roll": imu_roll,
                # "imu_pitch": imu_pitch,
                # "imu_yaw": imu_yaw
            }
        except struct.error:
            logger.warning("failed to parse telemetry frame")
            return None

    async def stop(self) -> None:
        self._running = False
        logger.info("telemetry collector stopped")
