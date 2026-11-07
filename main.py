import asyncio
import logging
import signal

from config import *
from uart import SerialLink
from network.ws_client import WebSocketClient
from network.webrtc_client import WebRTCClient
from camera.capture import CameraCapture
from core.raid_handler import RaidHandler
from core.telemetry import TelemetryCollector

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("spidor")


async def main():
    logger.info("SPIDOR Neocortex starting... ID = %s", ROBOT_ID)

    serial_link = SerialLink(UART_PORT, UART_BAUD)
    ws_client = WebSocketClient(PARA_RAID_URL, ROBOT_ID)
    camera = CameraCapture(CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)
    handler = RaidHandler(serial_link)
    telemetry = TelemetryCollector(serial_link, ws_client)
    webrtc = WebRTCClient(camera, ws_client)

    await serial_link.connect()
    await ws_client.connect()
    await camera.start()
    await webrtc.setup()

    ws_client.on("command", handler.handle_server_command)
    ws_client.on("start_video", lambda msg: webrtc.start_offer())

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    tasks = [
        asyncio.create_task(ws_client.listen(), name="ws_listen"),
        asyncio.create_task(telemetry.run(), name="telemetry"),
    ]

    if camera.running:
        tasks.append(asyncio.create_task(camera.run_continuous(), name="camera"))

    await shutdown_event.wait()

    logger.info("shutting down...")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    await webrtc.stop()
    await camera.stop()
    await telemetry.stop()
    await ws_client.disconnect()
    await serial_link.disconnect()

    logger.info("SPIDOR Neocortex stopped")


if __name__ == "__main__":
    asyncio.run(main())
