from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def include(name, enabled):
    launch_file = PathJoinSubstitution([FindPackageShare('pug_bringup'), 'launch', name])
    
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(launch_file),
        condition=IfCondition(LaunchConfiguration(enabled))
    )

def generate_launch_description():
    hardware = LaunchConfiguration('hardware')
    robot = LaunchConfiguration('robot')
    config_dir = PathJoinSubstitution(
        [FindPackageShare('pug_bringup'), 'config', 'robots', robot])

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'), ' ',
            PathJoinSubstitution([FindPackageShare('pug_description'), 'urdf', 'pug.urdf.xacro']),
            ' hardware:=', hardware,
            ' servo_config:=', PathJoinSubstitution([config_dir, 'servo.yaml']),
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument('hardware', default_value='mock', description='mock | real | mujoco'),
        DeclareLaunchArgument('robot', default_value='rospug_01'),
        DeclareLaunchArgument('monitoring', default_value='true'),
        DeclareLaunchArgument('teleop', default_value='true'),
        DeclareLaunchArgument('display', default_value='true'),
        DeclareLaunchArgument('mcu', default_value='true'),

        include('monitoring.launch.py', 'monitoring'),
        include('teleop.launch.py', 'teleop'),
        include('display.launch.py', 'display'),
        include('mcu.launch.py', 'mcu'),

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_description}]),
        Node(package='controller_manager', executable='ros2_control_node',
             parameters=[{'robot_description': robot_description},
                         PathJoinSubstitution([config_dir, 'controllers.yaml'])], output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster', '-c', '/controller_manager']),
        Node(package='controller_manager', executable='spawner',
                arguments=['forward_position_controller', '-c', '/controller_manager']),
    ])