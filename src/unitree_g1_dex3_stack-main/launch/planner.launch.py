from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration

def launch_setup(context, *args, **kwargs):
    # Parse collision_skip_pairs as a list from a comma-separated string
    collision_skip_pairs_str = LaunchConfiguration('collision_skip_pairs').perform(context)
    collision_skip_pairs = collision_skip_pairs_str.split(',') if collision_skip_pairs_str else []

    # All other parameters must be resolved to Python types (not LaunchConfiguration) for OpaqueFunction
    trajectory_time_step = float(LaunchConfiguration('trajectory_time_step').perform(context))
    planning_timeout = float(LaunchConfiguration('planning_timeout').perform(context))
    base_link = str(LaunchConfiguration('base_link').perform(context))
    right_tip = str(LaunchConfiguration('right_tip').perform(context))
    tcp_offset_x = float(LaunchConfiguration('tcp_offset_x').perform(context))
    planner_type = str(LaunchConfiguration('planner_type').perform(context))

    parameters = {
        'trajectory_time_step': trajectory_time_step,
        'planning_timeout': planning_timeout,
        'base_link': base_link,
        'right_tip': right_tip,
        'tcp_offset_x': tcp_offset_x,
        'planner_type': planner_type,
    }
    if collision_skip_pairs:
        parameters['collision_skip_pairs'] = collision_skip_pairs

    return [
        Node(
            package='unitree_g1_dex3_stack',
            executable='ik_fcl_ompl_planner',
            name='ik_fcl_ompl_planner',
            output='screen',
            parameters=[parameters],
            arguments=[
                '--ros-args',
                '--log-level',
                'trac_ik.ros.trac_ik:=DEBUG'
            ]
        )
    ]

def generate_launch_description():
    args = [
        DeclareLaunchArgument('trajectory_time_step', default_value='0.05'),
        DeclareLaunchArgument('planning_timeout', default_value='1.0'),
        DeclareLaunchArgument('base_link', default_value='torso_link'),
        DeclareLaunchArgument('right_tip', default_value='right_tcp_link'),
        DeclareLaunchArgument('tcp_offset_x', default_value='0.175'),
        DeclareLaunchArgument('planner_type', default_value='RRTConnect'),
        DeclareLaunchArgument('collision_skip_pairs', default_value='right_hand_thumb_0_link:right_wrist_yaw_link'),
    ]
    return LaunchDescription(args + [OpaqueFunction(function=launch_setup)])
