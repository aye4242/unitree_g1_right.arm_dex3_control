from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_share = get_package_share_directory('unitree_g1_dex3_stack')

    target_class_arg = DeclareLaunchArgument(
        'target_class',
        default_value='bottle',
        description='Object class to monitor and print when pressing s'
    )
    model_path_arg = DeclareLaunchArgument(
        'model_path',
        default_value='/home/unitree/Desktop/unitree_dex3/best.pt',
        description='Path to YOLO model file'
    )
    imshow_arg = DeclareLaunchArgument(
        'imshow',
        default_value='true',
        description='Whether to open an OpenCV display window'
    )
    detection3d_topic_arg = DeclareLaunchArgument(
        'detection3d_topic',
        default_value='/detections_3d',
        description='Detection3DArray topic produced by the perception pipeline'
    )
    pointcloud_topic_arg = DeclareLaunchArgument(
        'pointcloud_topic',
        default_value='/objects_3d',
        description='Projected object point cloud topic'
    )
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

    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, 'launch', 'perception.launch.py')
        ),
        launch_arguments={
            'model_path': LaunchConfiguration('model_path'),
            'imshow': LaunchConfiguration('imshow'),
            'pointcloud_topic': LaunchConfiguration('pointcloud_topic'),
            'detection3d_topic': LaunchConfiguration('detection3d_topic'),
            'output_frame': 'camera_color_optical_frame',
            'allowed_classes': ["['", LaunchConfiguration('target_class'), "']"],
        }.items()
    )

    d435_to_camera_link = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='d435_link_to_camera_link',
        arguments=['0', '0', '0', '0', '0', '0', 'd435_link', 'camera_link'],
    )

    visual_detection_yolo_tester = Node(
        package='unitree_g1_dex3_stack',
        executable='visual_detection_yolo_tester',
        name='visual_detection_yolo_tester',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'detections_topic': LaunchConfiguration('detection3d_topic'),
            'target_class': LaunchConfiguration('target_class'),
            'robot_frame': 'torso_link',
        }]
    )

    return LaunchDescription([
        target_class_arg,
        model_path_arg,
        imshow_arg,
        detection3d_topic_arg,
        pointcloud_topic_arg,
        urdf_name_arg,
        urdf_path_arg,
        robot_launch,
        perception_launch,
        d435_to_camera_link,
        visual_detection_yolo_tester,
    ])
