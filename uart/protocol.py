from enum import IntEnum
from typing import overload, Any


HEADER = bytes([0xAA, 0x55])


class Command(IntEnum):
    MOVE = 0x01
    STOP = 0x02
    SET_GAIT = 0x03
    SET_POSE = 0x04
    REQUEST_TELEMETRY = 0x05
    SET_LED = 0x06
    HOME = 0x07


class Frame:
    @overload
    def __init__(self, command: int, payload: bytes = b""): ...

    @overload
    def __init__(self, raw: bytes): ...

    def __init__(self, *args: Any, **kwargs: Any):
        do_raw = do_manual = False
        raw: bytes | None = None
        command_id: int | None = None
        payload: bytes | None = None

        # raw route
        if len(args) == 1 and isinstance(args[0], bytes):
            raw = args[0]
            do_raw = True
        elif len(kwargs) == 1 and isinstance(kwargs["raw"], bytes):
            raw = kwargs.get("raw", None)
            do_raw = True

        # manual configuration route
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], bytes):
            command_id = args[0]
            payload = args[1]
            do_manual = True
        elif len(kwargs) == 2 and isinstance(kwargs["command_id"], int) and isinstance(kwargs["payload"], bytes):
            command_id = kwargs.get("command_id", None)
            payload = kwargs.get("payload", None)
            do_manual = True

        else:
            raise RuntimeError("Invalid arguments")

        if do_raw and raw is not None:
            header = raw[0:2]
            if header != HEADER:
                raise ValueError("Header mismatch")
            self.length = raw[2]
            if len(raw) != self.length + 4:
                raise ValueError("Payload length mismatch")
            self.command_id = raw[3]
            self.payload = raw[4:4 + self.length]
            self._crc = raw[4 + self.length]
            if self._crc != self._crc8(raw[:4 + self.length]):
                raise ValueError("CRC mismatch")
        elif do_manual and command_id is not None and payload is not None:
            if command_id not in (c.value for c in Command):
                raise ValueError("Command mismatch")

            self.command_id = command_id
            self.length = len(payload)
            self.payload = payload

            self._body = HEADER + bytes([self.length, self.command_id]) + self.payload
            self._crc = self._crc8(self._body)
        else:
            raise ValueError("Invalid arguments: got None after parsing")

    def __eq__(self, other: Any) -> bool:
        return self._crc == other._crc and self.length == other.length and self.command_id == other.command_id

    @staticmethod
    def _crc8(data: bytes) -> int:
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc


    def encode(self) -> bytes:
        return self._body + bytes([self._crc])
