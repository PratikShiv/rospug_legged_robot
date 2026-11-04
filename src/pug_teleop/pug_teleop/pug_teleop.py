"""Publish a shaped /body_cmd from /joy at a fixed rate"""

from dataclasses import fields
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from pug_interfaces.msg import BodyCommand, RobotMode
from pug_interfaces.srv import SetMode
from pug_teleop.shaping import TeleopConfig, TeleopShaper
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Joy

class PugTeleop(Node):

    def __init__(self):
        super().__init__('pug_teleop')
        defaults = TeleopConfig()
        values = {f.name: self.declare_parameter(f.name, getattr(defaults, f.name)).value
                  for f in fields(TeleopConfig)}
        self.shaper = TeleopShaper(TeleopConfig(**values))
        
        self.pub = self.create_publisher(BodyCommand, 'body_cmd', 1)
        self.create_subscription(Joy, 'joy', self._on_joy, qos_profile_sensor_data)
        self.mode_client = self.create_client(SetMode, '/mode_manager/mode_set')
        self.create_timer(1.0 / self.shaper.cfg.rate_hz, self._step)

        self.updater = Updater(self, period=1.0)
        self.updater.setHardwareID('gamepad')
        self.updater.add('Joystick', self._fill)

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_joy(self, msg):
        self.shaper.on_joy(msg.axes, msg.buttons, self._now())

    def _step(self):
        now = self.get_clock().now()
        (vx, vy, yaw), requests = self.shaper.step(now.nanoseconds * 1e-9)
        msg = BodyCommand()
        msg.header.stamp = now.to_msg()
        msg.twist.linear.x, msg.twist.linear.y, msg.twist.angular.z = vx, vy, yaw
        self.pub.publish(msg)
        for name in requests:
            self._request_mode(name)

    def _request_mode(self, name):
        self.get_logger().info(f'mode request: {name}')
        if not self.mode_client.service_is_ready():
            self.get_logger().warn('/mode_manager/set_mode is not up yet', once=True)
            return

        future = self.mode_client.call_async(SetMode.Request(mode=getattr(RobotMode, name)))
        future.add_done_callback(lambda done: self._on_mode_reply(name, done))

    def _on_mode_reply(self, name, future):
        reply = future.result()
        if reply is not None and not reply.accepted:
            self.get_logger().warn(f'{name} refused: {reply.reason}')

    def _fill(self, stat):
        now = self._now()
        age = self.shaper.joy_age(now)

        if self.shaper.connected(now):
            stat.summary(DiagnosticStatus.OK, 'joystick connected')
        elif age is None:
            stat.summary(DiagnosticStatus.WARN, 'Waiting for /joy')
        else:
            stat.summary(DiagnosticStatus.WARN, f'no /joy for {age:.1f} s')
        stat.add('jot_age_s', 'none' if age is None else f'{age:.3f}')

        for name, value in zip(('vx', 'vy', 'yaw_rate'), self.shaper.command):
            stat.add(name, f'{value:.3f}')

        return stat


def main():
    rclpy.init()
    node = PugTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()