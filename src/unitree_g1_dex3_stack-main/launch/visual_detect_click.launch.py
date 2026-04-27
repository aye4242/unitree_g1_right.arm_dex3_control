from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_share = get_package_share_directory('unitree_g1_dex3_stack')
    realsense_share = get_package_share_directory('realsense2_camera')

    urdf_name_arg = DeclareLaunchArgument(
        'urdf_name',
        default_value='g1_29dof_lock_waist_with_hand_rev_1_0.urdf',
        description='URDF filename used by robot_state_publisher'
    )
    urdf_path_arg = DeclareLaunchArgument(
        'urdf_path',
        default_value='',
        description='Optional full URDF path that overrides urdf_name'
    )

    robot_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, 'launch', 'robot.launch.py')
        ),
        launch_arguments={
            'urdf_name': LaunchConfiguration('urdf_name'),
            'urdf_path': LaunchConfiguration('urdf_path'),
        }.items()
    )

    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(realsense_share, 'launch', 'rs_launch.py')
        ),
        launch_arguments={
            'enable_sync': 'true',
            'align_depth.enable': 'true',
            'rgb_camera.profile': '1280x720x15',
            'depth_module.profile': '1280x720x15',
        }.items()
    )

    d435_to_camera_link = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='d435_link_to_camera_link',
        arguments=['0', '0', '0', '0', '0', '0', 'd435_link', 'camera_link'],
    )

    visual_detection_click_tester = Node(
        package='unitree_g1_dex3_stack',
        executable='visual_detection_tester',
        name='visual_detection_click_tester',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'rgb_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/aligned_depth_to_color/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'display_topic': '',
            'robot_frame': 'torso_link',
        }]
    )

    return LaunchDescription([
        urdf_name_arg,
        urdf_path_arg,
        robot_launch,
        realsense_launch,
        d435_to_camera_link,
        visual_detection_click_tester,
    ])
