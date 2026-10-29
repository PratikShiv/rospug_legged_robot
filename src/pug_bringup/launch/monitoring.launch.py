from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    monitoring_cfg = PathJoinSubstitution(
        [FindPackageShare('pug_monitoring'), 'config', 'jetson_monitor.yaml'])
    diag_cfg = PathJoinSubstitution(
        [FindPackageShare('pug_bringup'), 'config', 'diagnostics.yaml'])

    return LaunchDescription([
        Node(package='pug_monitoring', executable='jetson_monitor', parameters=[monitoring_cfg]),
        Node(package='diagnostic_aggregator', executable='aggregator_node', name='analyzers',
             parameters=[diag_cfg]),
    ])