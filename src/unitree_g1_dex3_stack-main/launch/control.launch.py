from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import OpaqueFunction


def launch_setup(context, *args, **kwargs):
    return [
        Node(
            package='unitree_g1_dex3_stack',
            executable='joint_trajectory_executor',
            name='joint_trajectory_executor',
            output='screen'
        )
    ]


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=launch_setup)
    ])
