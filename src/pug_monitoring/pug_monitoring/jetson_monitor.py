"""Publish Jetson Power rails, temperatures and fan state on /diagnostics"""

from dataclasses import fields
import sys

from diagnostic_updater import Updater
from jtop import jtop, JtopException
from pug_monitoring.jetson_health import Thresholds, parse_jtop, evaluate
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.node import Node


class JetsonMonitor(Node):
    """Wrap jtop readings in a diagnostic_updater task"""

    def __init__(self):
        super().__init__('jetson_monitor')
        defaults = Thresholds()
        values = {f.name: self.declare_parameter(f.name, getattr(defaults, f.name)).value
                  for f in fields(Thresholds)}
        self.thresholds = Thresholds(**values)
        rate_hz = self.declare_parameter('rate_hz', 1.0).value
        hardware_id = self.declare_parameter('hardware_id', 'jetson').value
        self.add_on_set_parameters_callback(self._on_set_parameters)

        self.jetson = jtop()
        self.jetson.start()
        self.updater = Updater(self, period=1.0/rate_hz)
        self.updater.setHardwareID(hardware_id)
        self.updater.add('Jetson', self._fill)

    def _on_set_parameters(self, params):
        values = {f.name: getattr(self.thresholds, f.name) for f in fields(Thresholds)}
        for param in params:
            if param.name in values:
                values[param.name] = param.value
        self.thresholds = Thresholds(**values)
        return SetParametersResult(successful=True)

    def _fill(self, stat):
        temps, rails, fans = parse_jtop(self.jetson.temperature, self.jetson.power, self.jetson.fan)
        level, message = evaluate(temps, rails, fans, self.thresholds)

        for name, temp in temps.items():
            stat.add(f'temp_{name}', f'{temp:.1f} C')

        for name, (volt, curr) in rails.items():
            stat.add(f'{name}_V', f'{volt:.3f}')
            stat.add(f'{name}_A', f'{curr:.3f}')

        for name, (speed, rpm) in fans.items():
            stat.add(f'{name}_speed', f'{speed}')
            stat.add(f'{name}_rpm', f'{rpm}')

        stat.add('nvpmodel', str(getattr(self.jetson, 'nvpmodel', 'unknown')))
        stat.summary(bytes([level]), message)
        return stat


def main():
    rclpy.init()
    try:
        node = JetsonMonitor()
    except JtopException as err:
        print(f'Failed to start jtop: {err}. Is the jtop.service running?', file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(1)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.jetson.close()
        node.destroy_node()
        rclpy.shutdown()