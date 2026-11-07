import asyncio
import json
import logging
from typing import Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Awaitable[None]]


class WebSocketClient:
    def __init__(self, url: str, robot_id: str):
        self._url = url
        self._robot_id = robot_id
        self._connection: ClientConnection | None = None
        self._handlers: dict[str, MessageHandler] = {}
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def on(self, message_type: str, handler: MessageHandler) -> None:
        self._handlers[message_type] = handler

    async def connect(self) -> None:
        try:
            self._connection = await websockets.connect(self._url)
            self._connected = True
            await self.send_message("status", {"state": "online", "robot_id": self._robot_id})
            logger.info("WS connected to %s", self._url)
        except:
            self._connected = False
            logger.warning("WS unavailable at %s", self._url)

    async def send_message(self, msg_type: str, payload: dict) -> None:
        if not self._connected or self._connection is None:
            logger.debug("send skipped, UART not connected")
            return
        message = {"type": msg_type, "robot_id": self._robot_id, **payload}
        try:
            await self._connection.send(json.dumps(message))
        except Exception as e:
            logger.warning("WS send error: %s", e)
            self._connected = False

    async def listen(self) -> None:
        while True:
            if not self._connected or self._connection is None:
                await asyncio.sleep(5)
                await self.connect()
                continue
            try:
                raw = await self._connection.recv()
                message = json.loads(raw)
                msg_type = message.get("type", "")
                handler = self._handlers.get(msg_type)
                if handler:
                    await handler(message)
                else:
                    logger.debug("unhandled message type: %s", msg_type)
            except websockets.ConnectionClosed:
                logger.warning("WS connection closed, reconnecting")
                self._connected = False
            except Exception as e:
                logger.warning("WS listen error: %s", e)
                self._connected = False

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
        self._connected = False
        logger.info("WS disconnected")
