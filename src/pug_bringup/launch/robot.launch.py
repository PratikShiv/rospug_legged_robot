from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def include(name, enabled):
    launch_file = PathJoinSubstitution(
        [FindPackageShare('pug_bringup'), 'launch', name])
    
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(launch_file),
        condition=IfCondition(LaunchConfiguration(enabled))
    )

def generate_launch_description():

    return LaunchDescription([
        DeclareLaunchArgument('monitoring', default_value='true'),
        DeclareLaunchArgument('teleop', default_value='true'),
        DeclareLaunchArgument('display', default_value='true'),
        DeclareLaunchArgument('mcu', default_value='true'),

        include('monitoring.launch.py', 'monitoring'),
        include('teleop.launch.py', 'teleop'),
        include('display.launch.py', 'display'),
        include('mcu.launch.py', 'mcu'),
    ])