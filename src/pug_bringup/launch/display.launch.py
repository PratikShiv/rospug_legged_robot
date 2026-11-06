from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    display_cfg = PathJoinSubstitution(
        [FindPackageShare('pug_display'), 'config', 'oled.yaml'])
    return LaunchDescription([
        Node(package='pug_display', executable='oled_display', parameters=[display_cfg]),
    ])