from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def launch_setup(context, *args, **kwargs):
    allowed_classes_str = LaunchConfiguration('allowed_classes').perform(context)
    if allowed_classes_str.strip() == '' or allowed_classes_str.strip() == '[]':
        allowed_classes = []
    else:
        import ast
        try:
            allowed_classes = ast.literal_eval(allowed_classes_str)
            if not isinstance(allowed_classes, list):
                allowed_classes = [allowed_classes]
        except Exception:
            allowed_classes = [allowed_classes_str]

    model_path = str(LaunchConfiguration('model_path').perform(context))
    pointcloud_topic = str(LaunchConfiguration('pointcloud_topic').perform(context))
    detection3d_topic = str(LaunchConfiguration('detection3d_topic').perform(context))
    output_frame = str(LaunchConfiguration('output_frame').perform(context))
    imshow = LaunchConfiguration('imshow')

    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('realsense2_camera'),
                'launch',
                'rs_launch.py'
            )
        ),
        launch_arguments={
            'enable_sync': 'true',
            'align_depth.enable': 'true',
            'rgb_camera.profile': '1280x720x15',
            'depth_module.profile': '1280x720x15',
        }.items()
    )

    detector_node = Node(
        package='unitree_g1_dex3_stack',
        executable='ultralytics_detector.py',
        name='ultralytics_detector',
        output='screen',
        emulate_tty=True,
        parameters=[{
            "model_path": model_path,
            "conf": 0.3,
            "nms": 0.45,
            "imshow_isshow": imshow,
            "src_image_topic_name": '/camera/color/image_raw',
            "publish_image_topic_name": '/yolo/image_raw',
            "publish_boundingbox_topic_name": '/yolo/bounding_boxes',
        }]
    )

    project_to_3d_node = Node(
        package='unitree_g1_dex3_stack',
        executable='project_to_3d_node',
        name='project_to_3d_node',
        output='screen',
        parameters=[{
            'rgb_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/aligned_depth_to_color/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'detections_topic': '/yolo/bounding_boxes',
            'pointcloud_topic': pointcloud_topic,
            'detection3d_topic': detection3d_topic,
            'output_frame': output_frame,
            'allowed_classes': allowed_classes,
        }]
    )

    detection_to_goal_node = Node(
        package='unitree_g1_dex3_stack',
        executable='detection_to_goal_node',
        name='detection_to_goal_node',
        output='screen',
        parameters=[{
            'detections': detection3d_topic,
            'detection_selection': '/detection_selection',
            'goal_pose': '/goal_pose',
        }]
    )

    # Wait for other nodes to launch before realsense
    realsense_launch_delayed = TimerAction(period=5.0, actions=[realsense_launch])

    return [
        detector_node,
        project_to_3d_node,
        detection_to_goal_node,
        realsense_launch_delayed
    ]

def generate_launch_description():
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
    pointcloud_topic_arg = DeclareLaunchArgument(
        'pointcloud_topic',
        default_value='/objects_3d',
        description='Output topic for projected 3D point cloud'
    )
    detection3d_topic_arg = DeclareLaunchArgument(
        'detection3d_topic',
        default_value='/detections_3d',
        description='Output topic for Detection3DArray'
    )
    output_frame_arg = DeclareLaunchArgument(
        'output_frame',
        default_value='camera_color_optical_frame',
        description='Output frame for projected data'
    )
    allowed_classes_arg = DeclareLaunchArgument(
        'allowed_classes',
        default_value="['cup','bottle','book','bowl']",
        description='Allowed classes for projection node (as Python list string, or empty for all)'
    )

    return LaunchDescription([
        model_path_arg,
        imshow_arg,
        pointcloud_topic_arg,
        detection3d_topic_arg,
        output_frame_arg,
        allowed_classes_arg,
        OpaqueFunction(function=launch_setup)
    ])
