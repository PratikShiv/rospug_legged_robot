"""Show the IP address, health and mode on the OLED display."""

import socket
import subprocess
import sys

from diagnostic_msgs.msg import DiagnosticStatus, DiagnosticArray
from diagnostic_updater import Updater
from luma.core.error import Error as LumaError
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from pug_display.pages import (battery_text, battery_volts, health_lines, network_lines, page_at, title)
from pug_interfaces.msg import RobotMode
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile

MODES = ('BOOT', 'IDLE', 'STANDING_UP', 'STAND', 'WALK', 'SITTING', 'SAFE_STOP', 'ESTOP')

SETUP = (0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8,
         0xDA, 0x02, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0x81, 0xCF, 0xAF)


class TolerantI2C:
    """Wrap luma's i2c interface so errors are recorded instead of raised"""

    def __init__(self, port, address):
        self.serial = i2c(port=port, address=address)
        self.error = None

    def command(self, *cmd):
        self._send(self.serial.command, *cmd)

    def data(self, *data):
        self._send(self.serial.data, *data)

    def cleanup(self):
        self.serial.clean_up

    def _send(self, send, *args):
        try:
            send(*args)
        except (OSError, LumaError) as err:
            self.error = str(err)


class OledDisplay(Node):
    """Draw a title bar with the mode, then the network or health page, once a second"""

    def __init__(self):
        super().__init__('oled_display')
        bus = self.declare_parameter('i2c_bus', 7).value
        address = self.declare_parameter('i2c_address', 0x3C).value
        self.page_period_s = self.declare_parameter('page_period_s', 4.0).value
        self.battery_cells = self.declare_parameter('battery_cells', 3).value
        rate_hz = self.declare_parameter('rate_hz', 1.0).value

        self.serial = TolerantI2C(bus, address)
        self.device = ssd1306(self.serial, width=128, height=32, rotate=0)
        self.mode_names = {getattr(RobotMode, name): name for name in MODES}
        self.mode = None
        self.statuses = []
        self.battery_v = None

        self.create_subscription(DiagnosticArray, '/diagnostics_agg', self._on_diagnostics, 1)
        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(RobotMode, '/robot_mode', self._on_mode, latched)
        self.create_timer(1.0 / rate_hz, self._refresh)

        self.updater = Updater(self, period=1.0)
        self.updater.setHardwareID(f'ssd1306 i2c-{bus} 0x{address:02X}')
        self.updater.add('Display', self._fill)

    def _on_diagnostics(self, msg):
        self.statuses = [(s.name, ord(s.level), s.message) for s in msg.status]
        self.battery_v = battery_volts(
            [(s.name, ord(s.level), {v.key: v.value for v in s.values}) for s in msg.status])

    def _on_mode(self, msg):
        self.mode = self.mode_names.get(msg.mode, str(msg.mode))

    def _refresh(self):
        now = self.get_clock().now().nanoseconds * 1e-9
        if page_at(now, self.page_period_s, 2) == 0:
            addresses = subprocess.run(['hostname', '-I'], capture_output=True, text=True).stdout
            lines = network_lines(addresses, socket.gethostname())
        else:
            lines = health_lines(self.statuses)
        battery = battery_text(self.battery_v, self.battery_cells)
        self.serial.error = None
        self.device.command(*SETUP)
        with canvas(self.device) as draw:
            draw.rectangle((0, 0, 127, 10), fill='white')
            draw.text((2, 0), battery, fill='black')
            mode = title(self.mode)
            draw.text((126 - draw.textlength(mode), 0), mode, fill='black')
            draw.text((2, 11), lines[0], fill='white')
            draw.text((2, 21), lines[1], fill='white')

    def _fill(self, stat):
        if self.serial.error is None:
            stat.summary(DiagnosticStatus.OK, 'drawing')
        else:
            stat.summary(DiagnosticStatus.WARN, f'OLED not answering: {self.serial.error}')

        stat.add('page_period_s', str(self.page_period_s))
        stat.add('battery', battery_text(self.battery_v, self.battery_cells))
        return stat


def main():
    rclpy.init()
    try:
        node = OledDisplay()
    except LumaError as err:
        print(f'Failed to initialize OLED display: {err}', file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(1)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()