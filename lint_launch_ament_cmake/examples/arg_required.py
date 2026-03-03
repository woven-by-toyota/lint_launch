import launch


def generate_launch_description():
    return launch.LaunchDescription(
        [
            launch.actions.DeclareLaunchArgument("foo", description="A required argument"),
        ]
    )
