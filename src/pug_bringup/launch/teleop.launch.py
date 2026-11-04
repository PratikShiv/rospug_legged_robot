from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    teleop_cfg = PathJoinSubstitution(
        [FindPackageShare('pug_teleop'), 'config', 'xbox.yaml'])

    return LaunchDescription([
        Node(package='joy', executable='game_controller_node',
             parameters=[{'autorepeat_rate': 50.0, 'deadzone': 0.0}]),
        Node(package='pug_teleop', executable='pug_teleop', parameters=[teleop_cfg]),
    ])