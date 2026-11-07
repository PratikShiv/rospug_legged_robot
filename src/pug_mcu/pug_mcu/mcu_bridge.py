"""Publish the adaptor board's IMU and battery voltage to ROS topics"""

import sys

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from diagnostic_updater import Updater
from pug_mcu.mcu_protocol import decode_battery, decode_imu, FrameParser, FUNC_IMU, FUNC_SYS
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
import serial


class McuBridge(Node):
    """Own the MCU serual link"""

    def __init__(self):
        super().__init__('mcu_bridge')
        port = self.declare_parameter('port', '/dev/ttyTHS1').value
        baud = self.declare_parameter('baud', 500000).value
        self.frame_id = self.declare_parameter('frame_id', 'imu_link').value
        self.battery_warn_v = self.declare_parameter('battery_warn_v', 10.5).value

        self.serial = serial.Serial(port, baud, timeout=0)
        self.parser = FrameParser()
        self.imu_times = []
        self.battery_v = None
        self.pub = self.create_publisher(Imu, 'imu/data_raw', qos_profile_sensor_data)
        self.create_timer(0.005, self._poll)

        self.updater = Updater(self, period=1.0)
        self.updater.setHardwareID(f'at32 {port}')
        self.updater.add('MCU link', self._fill)

    def _poll(self):
        now = self.get_clock().now()
        for func, payload in self.parser.feed(self.serial.read(self.serial.in_waiting)):
            if func == FUNC_IMU:
                imu = decode_imu(payload)
                if imu is not None:
                    self._publish(now, *imu)
            elif func == FUNC_SYS:
                volts = decode_battery(payload)
                if volts is not None:
                    self.battery_v = volts

    def _publish(self, now, accel, gyro):
        msg = Imu()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = self.frame_id
        msg.orientation_covariance[0] = -1.0
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = accel
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = gyro
        self.pub.publish(msg)
        self.imu_times.append(now.nanoseconds * 1e-9)

    def _fill(self, stat):
        now = self.get_clock().now().nanoseconds * 1e-9
        self.imu_times = [t for t in self.imu_times if t > now - 1.0]
        rate = len(self.imu_times)
        if rate == 0:
            stat.summary(DiagnosticStatus.ERROR, 'no IMU: board off?')
        elif self.battery_v is not None and self.battery_v < self.battery_warn_v:
            stat.summary(DiagnosticStatus.WARN, f'battery low: {self.battery_v:.2f} V')
        else:
            stat.summary(DiagnosticStatus.OK, f'IMU {rate} Hz')
        stat.add('imu_rate_hz', str(rate))
        stat.add('battery_V', 'none' if self.battery_v is None else f'{self.battery_v:.2f}')
        stat.add('crc_errrors', str(self.parser.crc_errors))
        return stat

def main():
    rclpy.init()
    try:
        node = McuBridge()
    except serial.SerialException as err:
        print(f'mcu_bridge: {err}. Check the port in config/mcu.yaml, the dialout group', file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(1)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.serial.close()
        node.destroy_node()
        rclpy.try_shutdown()