"""Encode and decode frames from the AT32 MCU bridge."""
import math
import struct

# Frames are 0xAA, 0x55, <func> <len> <data> <crc>
FUNC_SYS, FUNC_BUS_SERVO, FUNC_IMU = 0, 5, 7
FUNC_COUNT = 12
BATTERY_REPORT = 0x04
GRAVITY = 9.80665

def cr8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8C if crc & 1 else 0)
    return crc

def encode(func, data):
    """Encode a frame to send to the MCU"""
    body = bytes([func, len(data)]) + bytes(data)
    return b'\xaa\x55' + body + bytes([cr8(body)])


class FrameParser:
    """Parse a stream of bytes into frames from the MCU"""

    def __init__(self):
        self.buf = bytearray()
        self.crc_errors = 0

    def feed(self, data):
        self.buf += data
        frames = []

        while True:
            start = self.buf.find(b'\xaa\x55')
            if start < 0:
                del self.buf[:-1]
                return frames
            del self.buf[:start]
            if len(self.buf) < 4:
                return frames
            func, length = self.buf[2], self.buf[3]
            if func >= FUNC_COUNT:
                del self.buf[:2]
                continue
            if len(self.buf) < 5 + length:
                return frames
            if cr8(self.buf[2:4 + length]) == self.buf[4 + length]:
                frames.append((func, bytes(self.buf[4:4 + length])))
                del self.buf[:5 + length]
            else:
                self.crc_errors += 1
                del self.buf[:2]


def decode_imu(payload):
    """Decode an IMU frame into a dict of floats"""
    if len(payload) != 24:
        return None

    ax, ay, az, gx, gy, gz = struct.unpack('<6f', payload)
    return (ax * GRAVITY, ay * GRAVITY, az * GRAVITY), tuple(map(math.radians, (gx, gy, gz)))

def decode_battery(payload):
    """Return the battery voltage in volts from a battery report frame"""
    if len(payload) != 3 or payload[0] != BATTERY_REPORT:
        return None
    return struct.unpack('<H', payload[1:3])[0] * 0.001