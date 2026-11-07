from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    mcu_cfg = PathJoinSubstitution([FindPackageShare('pug_mcu'), 'config', 'mcu.yaml'])
    return LaunchDescription([
        Node(package='pug_mcu', executable='mcu_bridge', parameters=[mcu_cfg])
    ])