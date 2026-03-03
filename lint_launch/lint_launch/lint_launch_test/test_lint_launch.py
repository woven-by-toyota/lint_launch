# Copyright 2026 Toyota Motor Corporation

import launch
import launch_ros
import pytest

from lint_launch.validation_error import ValidationError
from lint_launch.validators import (
    register_init_hooks,
    validate_condition,
    validate_launch_description,
    validate_node,
    validate_set_config,
    validate_source,
    validate_source_action,
    validate_timer,
)

register_init_hooks()


def test_empty() -> None:
    desc = launch.LaunchDescription()
    # Doesn't raise
    validate_launch_description(desc, [], launch.LaunchContext())


def test_extra_argument() -> None:
    desc = launch.LaunchDescription()
    with pytest.raises(ValidationError):
        validate_launch_description(desc, ["foo"], launch.LaunchContext())


def test_missing_argument() -> None:
    desc = launch.LaunchDescription()
    desc.add_action(launch.actions.DeclareLaunchArgument("foo"))
    with pytest.raises(ValidationError):
        validate_launch_description(desc, [], launch.LaunchContext())


def test_timer_negative() -> None:
    timer = launch.actions.TimerAction(period=-1.0, actions=[])
    with pytest.raises(ValidationError):
        validate_timer(timer, launch.LaunchContext(), [])


def test_non_existent_include() -> None:
    include = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource("/foo/bar/baz.launch.py")
    )
    with pytest.raises(ValidationError):
        validate_source_action(include, launch.LaunchContext(), [])


@pytest.mark.xfail(
    raises=ValidationError,
    reason=(
        "We need to have proper launch support in Bazel for this to pass,"
        "otherwise we can't find installed packages"
    ),
)
def test_existing_node() -> None:
    node = launch_ros.actions.Node(package="xacro", executable="xacro")
    validate_node(node, launch.LaunchContext())


def test_non_existent_package() -> None:
    node = launch_ros.actions.Node(package="foobar", executable="baz")

    with pytest.raises(ValidationError):
        validate_node(node, launch.LaunchContext())


def test_non_existent_node() -> None:
    node = launch_ros.actions.Node(package="xacro", executable="hoge")
    with pytest.raises(ValidationError):
        validate_node(node, launch.LaunchContext())


def test_non_existent_configuration_condition() -> None:
    action = launch.Action(condition=launch.conditions.LaunchConfigurationEquals("foobar", "hoge"))
    # This is a little misleading: in launch_configuration_equals, we get False
    # instead of an exception if we are using a non-existent configuration key...
    assert not validate_condition(action, launch.LaunchContext())


def test_non_existent_configuration_set_config() -> None:
    set_config = launch.actions.SetLaunchConfiguration(
        launch.substitutions.LaunchConfiguration("foo"), "abcd"
    )
    with pytest.raises(ValidationError):
        validate_set_config(set_config, launch.LaunchContext())


def test_simple_argument() -> None:
    desc = launch.LaunchDescription()
    desc.add_action(launch.actions.DeclareLaunchArgument("foo"))
    validate_source(
        launch.LaunchDescriptionSource(desc), [("foo", "bar")], launch.LaunchContext(), []
    )


def test_indirect_argument_passing() -> None:
    inner_desc = launch.LaunchDescription()
    inner_desc.add_action(launch.actions.DeclareLaunchArgument("foo"))
    include = launch.actions.IncludeLaunchDescription(
        launch.LaunchDescriptionSource(inner_desc),
    )
    outer_desc = launch.LaunchDescription()
    outer_desc.add_action(include)

    validate_source(
        launch.LaunchDescriptionSource(outer_desc), [("foo", "bar")], launch.LaunchContext(), []
    )


def generate_sibling_includes() -> (
    tuple[launch.actions.IncludeLaunchDescription, launch.actions.IncludeLaunchDescription]
):
    # This declares an argument, but it's not passed to the include
    first_sibling_desc = launch.LaunchDescription()
    first_sibling_desc.add_action(launch.actions.DeclareLaunchArgument("foo"))
    first_include = launch.actions.IncludeLaunchDescription(
        launch.LaunchDescriptionSource(first_sibling_desc),
    )

    # This gets the argument passed from the top-level, but doesn't declare it
    second_sibling_desc = launch.LaunchDescription()
    second_include = launch.actions.IncludeLaunchDescription(
        launch.LaunchDescriptionSource(second_sibling_desc),
        launch_arguments=[("foo", "bar")],
    )

    return first_include, second_include


def test_sibling_argument_passing() -> None:
    first_include, second_include = generate_sibling_includes()
    top_desc = launch.LaunchDescription()
    top_desc.add_action(first_include)
    top_desc.add_action(second_include)

    with pytest.raises(ValidationError):
        validate_source(launch.LaunchDescriptionSource(top_desc), [], launch.LaunchContext(), [])


def test_symmetrical_sibling_argument_passing() -> None:
    first_include, second_include = generate_sibling_includes()
    top_desc = launch.LaunchDescription()
    top_desc.add_action(second_include)
    top_desc.add_action(first_include)

    with pytest.raises(ValidationError):
        validate_source(launch.LaunchDescriptionSource(top_desc), [], launch.LaunchContext(), [])


def test_double_argument_definition() -> None:
    declare_foo = launch.actions.DeclareLaunchArgument("foo", default_value="bar")
    desc = launch.LaunchDescription([declare_foo, declare_foo])

    with pytest.raises(ValidationError):
        validate_launch_description(desc, [], launch.LaunchContext())


def test_double_argument_indirect_definition() -> None:
    declare_foo = launch.actions.DeclareLaunchArgument("foo", default_value="bar")
    inner_desc = launch.LaunchDescription([declare_foo])

    include_inner = launch.actions.IncludeLaunchDescription(
        launch.LaunchDescriptionSource(inner_desc)
    )
    outer_desc = launch.LaunchDescription([include_inner, declare_foo])

    with pytest.raises(ValidationError):
        validate_launch_description(outer_desc, [], launch.LaunchContext())


def test_double_sibling_argument_definition() -> None:
    inner_desc = launch.LaunchDescription(
        [launch.actions.DeclareLaunchArgument("foo", default_value="bar")]
    )
    include = launch.actions.IncludeLaunchDescription(launch.LaunchDescriptionSource(inner_desc))
    outer_desc = launch.LaunchDescription([include, include])

    # Doesn't raise because the different includes have their own scope
    validate_launch_description(outer_desc, [], launch.LaunchContext())
