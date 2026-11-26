import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.conditions import UnlessCondition, IfCondition
import xacro


def generate_launch_description():

    pkg_amr_description = get_package_share_directory('amr_description')
    pkg_amr_bringup = get_package_share_directory('amr_bringup')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    # pkg_amr_localization = get_package_share_directory('amr_localization')
    # pkg_amr_navigation = get_package_share_directory('amr_navigation')
      

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    use_simple_controller_arg = DeclareLaunchArgument(
        "use_simple_controller",
        default_value="True",
    )

    wheel_radius_arg = DeclareLaunchArgument(
        "wheel_radius",
        default_value="0.1",
    )

    wheel_separation_arg = DeclareLaunchArgument(
        "wheel_separation",
        default_value="0.65",
    )

    world_path_arg = DeclareLaunchArgument(
        "world_path",
        default_value="world.sdf"
    )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_simple_controller = LaunchConfiguration("use_simple_controller")
    wheel_radius = LaunchConfiguration("wheel_radius")
    wheel_separation = LaunchConfiguration("wheel_separation")
    world_path = LaunchConfiguration("world_path")

    urdf_file_path = os.path.join(pkg_amr_description, 'urdf', 'amr.xacro')
    world_file_path = PathJoinSubstitution(
        [
            pkg_amr_bringup,
            "worlds",
            world_path
        ]
    )

    gazebo_config_path = os.path.join(pkg_amr_description, 'config', 'gazebo_bridge.yaml')

    rviz_file_path = os.path.join(pkg_amr_bringup, 'rviz', 'amr_v1.rviz')
    
    robot_description_config = xacro.process_file(
                urdf_file_path,
                mappings={
                'width': '0.6',
                'wheel_radius': '0.1',
                'wheel_width': '0.05'
            })
    robot_description = {'robot_description': robot_description_config.toxml()}
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
        ]
    )
    
    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-r -v 4 ', world_file_path]
            # 'gz_args': ['-r -v 4 ', 'empty.sdf']
        }.items()
    )

    spawn_amr = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_amr",
        output="screen",
        arguments=[
            '-topic',   
            'robot_description',
            '-name','amr',
            '-x','1.0',
            '-y','0.0',
            '-z','0.0',
            '-Y','0.0'
        ],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        parameters=[
            {'use_sim_time': use_sim_time},
        ],
        arguments=['-d', rviz_file_path],
    )

    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="parameter_bridge",
        output="screen",
        parameters=[
            {'config_file': gazebo_config_path },
            {'use_sim_time': use_sim_time}
        ],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    amr_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["amr_controller", 
                   "--controller-manager", 
                   "/controller_manager"
        ],
        remappings=[
            ("/amr_controller/cmd_vel", "/cmd_vel"),
            ("/amr_controller/odom", "/odom"),
        ],
        
        condition=UnlessCondition(use_simple_controller),
    )

    simple_controller = GroupAction(
        condition=IfCondition(use_simple_controller),
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["simple_velocity_controller", 
                        "--controller-manager", 
                        "/controller_manager"
                ]
            ),
            Node(
                package="amr_controller",
                executable="simple_controller",
                parameters=[
                    {"wheel_radius": wheel_radius,
                    "wheel_separation": wheel_separation,
                    "use_sim_time": use_sim_time}],
            ),
        ]
    )

    # amr_global_localization = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(pkg_amr_localization, 'launch', 'global_localization.launch.py')
    #     ),
    # )
    # amr_navigation = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(pkg_amr_navigation, 'launch', 'amr_navigation.launch.py')
    #     ),
    # )

    # set_gz_plugin_path = SetEnvironmentVariable(
    #     name='GZ_SIM_SYSTEM_PLUGIN_PATH',
    #     value=[gz_ros2_control_lib, ':', os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', '')]
    # )

    return LaunchDescription([
        world_path_arg,
        use_simple_controller_arg,
        wheel_radius_arg,
        wheel_separation_arg,
        declare_use_sim_time_cmd,
        robot_state_publisher,
        gazebo_sim,
        spawn_amr,
        rviz_node,
        gazebo_bridge,
        joint_state_broadcaster_spawner,
        simple_controller,
        amr_controller_spawner,
        # amr_global_localization,
        # amr_navigation
    ])