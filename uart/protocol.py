from enum import IntEnum
from typing import overload, Any


HEADER = bytes([0xAA, 0x55])


class Command(IntEnum):
    CMD_MOVE = 0x01
    CMD_STOP = 0x02
    CMD_SET_GAIT = 0x03
    CMD_SET_POSE = 0x04
    CMD_REQUEST_TELEMETRY = 0x05
    CMD_SET_LED = 0x06
    CMD_HOME = 0x07


class Frame:
    @overload
    def __init__(self, command: int, payload: bytes): ...

    @overload
    def __init__(self, raw: bytes): ...

    def __init__(self, *args: Any, **kwargs: Any):
        # raw route
        if len(args) == 1 and isinstance(args[0], bytes):
            raw = args[0]
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

        # manual configuration route
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], bytes):
            if args[0] not in (c.value for c in Command):
                raise ValueError("Command mismatch")

            self.command_id = args[0]
            self.length = len(args[1])
            self.payload = args[1]

            self._body = HEADER + bytes([self.length, self.command_id]) + self.payload
            self._crc = self._crc8(self._body)

        else:
            raise RuntimeError("Invalid arguments")

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
