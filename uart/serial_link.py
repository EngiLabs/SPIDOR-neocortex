import asyncio
import logging

import serial_asyncio

from .protocol import Frame

logger = logging.getLogger(__name__)


class SerialLink:
    def __init__(self, port: str, baudrate: int):
        self._port = port
        self._baudrate = baudrate
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=self._baudrate,
            )
            self._connected = True
            logger.info("UART connected on %s @ %d", self._port, self._baudrate)
        except:
            self._connected = False
            logger.warning("UART unavailable on %s", self._port)

    async def send(self, frame: Frame) -> None:
        if not self._connected or self._writer is None:
            logger.debug("send skipped, UART not connected")
        else:
            data = frame.encode()
            self._writer.write(data)
            await self._writer.drain()

    async def receive(self) -> Frame | None:
        if not self._connected or self._reader is None:
            await asyncio.sleep(1)
            return None
        try:
            header = await self._reader.readexactly(2)
            length_byte = await self._reader.readexactly(1)
            body_crc = await self._reader.readexactly(length_byte[0] + 1)
            return Frame(header + length_byte + body_crc)
        except Exception as e:
            logger.warning("UART read error: %s", e)
            self._connected = False
            return None

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
        self._connected = False
        logger.info("UART disconnected")
