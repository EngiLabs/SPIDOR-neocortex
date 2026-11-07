import asyncio
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CameraCapture:
    def __init__(self, index: int, width: int, height: int, fps: int):
        self._index = index
        self._width = width
        self._height = height
        self._fps = fps
        self._cap: cv2.VideoCapture | None = None
        self._lock = asyncio.Lock()
        self._latest_frame: np.ndarray | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._cap = await loop.run_in_executor(None, self._open_capture)
        if self._cap and self._cap.isOpened():
            self._running = True
            logger.info("camera %d started (%dx%d @ %dfps)", self._index, self._width, self._height, self._fps)
        else:
            self._running = False
            logger.warning("camera %d unavailable", self._index)

    def _open_capture(self) -> cv2.VideoCapture | None:
        try:
            cap = cv2.VideoCapture(self._index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            cap.set(cv2.CAP_PROP_FPS, self._fps)
            return cap
        except:
            return None

    async def get_frame(self) -> np.ndarray | None:
        if not self._running or self._cap is None:
            return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_frame)

    def _read_frame(self) -> np.ndarray | None:
        if self._cap is None:
            return None
        ret, frame = self._cap.read()
        if ret:
            return frame
        return None

    async def run_continuous(self) -> None:
        while self._running:
            frame = await self.get_frame()
            if frame is not None:
                async with self._lock:
                    self._latest_frame = frame
            else:
                await asyncio.sleep(0.01)

    async def stop(self) -> None:
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("camera stopped")
