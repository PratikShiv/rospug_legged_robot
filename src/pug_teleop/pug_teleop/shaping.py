"""Shape gamepad input into velocity commands"""
from dataclasses import dataclass
import math

# Config field, requested mode
MODE_BUTTONS = (('button_stand', 'STAND'),
                ('button_sit', 'SITTING'),
                ('button_walk', 'WALK'),
                ('button_estop', 'ESTOP'))

@dataclass(frozen=True)
class TeleopConfig:
    """Axis and button indices, limits and timing."""

    axis_vx: int = 1
    axis_vy: int = 0
    axis_yaw: int = 2
    button_deadman: int = 9
    button_stand: int = 0
    button_sit: int = 1
    button_walk: int = 2
    button_estop: int = 4
    max_vx: float = 0.25
    max_vy: float = 0.15
    max_yaw: float = 0.8
    max_accel: float = 0.5
    deadzone: float = 0.08
    timeout_s: float = 0.5
    rate_hz: float = 50.0

def deadzone(value, width):
    """Return 0 inside the deadzone, then rise linearly from 0 at it's edge to 1 at full stick"""
    value = max(-1.0, min(1.0, value))
    if abs(value) <= width:
        return 0.0

    return math.copysign((abs(value) - width) / (1.0 - width), value)


def slew(current, target, max_step):
    """Move current towards target using a slew"""
    return current + max(-max_step, min(max_step, target - current))


def _get(values, index):
    """Return values[index] or 0 if the gamepad reports fewer axes or buttons"""
    return values[index] if 0 <= index < len(values) else 0


class TeleopShaper:
    """Turn jot samples into shaped (vx, vy, yaw rate) command and mode requests"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.command = (0.0, 0.0, 0.0)
        self._axes, self._buttons = (), ()
        self._last_joy = None
        self._timed_out = False
        self._requests = []

    def on_joy(self, axes, buttons, now):
        """Store one Joy Sample and queue a request for each mode button just pressed"""
        for field_name, mode in MODE_BUTTONS:
            index = getattr(self.cfg, field_name)
            if _get(buttons, index) and not _get(self._buttons, index):
                self._requests.append(mode)
        self._axes, self._buttons = tuple(axes), tuple(buttons)
        self._last_joy, self._timed_out = now, False

    def joy_age(self, now):
        """Return the seconds since the last joy sample"""
        return None if self._last_joy is None else now - self._last_joy

    def connected(self, now):
        """Return True if the last joy sample is recent enough to be considered connected"""
        age = self.joy_age(now)
        return age is not None and age < self.cfg.timeout_s

    def step(self, now):
        """Advance one cycle and return"""
        cfg = self.cfg
        if not self.connected(now):
            if self._last_joy is not None and not self._timed_out:
                self._timed_out = True
                self._requests.append('STAND')
            self.command = (0.0, 0.0, 0.0)
        elif not _get(self._buttons, cfg.button_deadman):
            self.command = (0.0, 0.0, 0.0)
        else:
            targets = (deadzone(_get(self._axes, cfg.axis_vx), cfg.deadzone) * cfg.max_vx,
                       deadzone(_get(self._axes, cfg.axis_vy), cfg.deadzone) * cfg.max_vy,
                       deadzone(_get(self._axes, cfg.axis_yaw), cfg.deadzone) * cfg.max_yaw)

            max_step = cfg.max_accel / cfg.rate_hz
            self.command = tuple(slew(c, t, max_step) for c, t in zip(self.command, targets))

        requests, self._requests = self._requests, []
        return self.command, requests