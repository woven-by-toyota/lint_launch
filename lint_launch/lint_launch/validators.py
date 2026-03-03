# Copyright 2026 Toyota Motor Corporation

import logging
from collections import OrderedDict
from typing import Any, Iterable, Tuple, cast

import launch
import launch_ros
from ament_index_python.packages import PackageNotFoundError
from launch.some_substitutions_type import SomeSubstitutionsType
from launch.utilities.type_utils import perform_typed_substitution

from .launch_tools import perform_all_substitutions, register_init
from .validation_error import ValidationError

logger = logging.getLogger(__name__)


def validate_node(node: launch_ros.actions.Node, context: launch.LaunchContext, *_: Any) -> None:
    logger.info("Validating node %s", node)
    # Validate that the executable exists here!
    if node._Node__node_executable == "/not/available/in/bazel":
        return
    subst = launch_ros.substitutions.ExecutableInPackage(
        node._Node__node_executable, node._Node__package
    )
    # This will raise if the package / node is not found
    try:
        subst.perform(context)
    except (
        launch.substitutions.SubstitutionFailure,
        PackageNotFoundError,
    ) as e:
        filename, lineno = node.__location__
        raise ValidationError(str(e) + f" In {filename}:{lineno}") from e


def validate_source_action(
    include: launch.actions.IncludeLaunchDescription,
    context: launch.LaunchContext,
    passed_arguments: list[str],
) -> None:
    try:
        validate_source(
            include.launch_description_source,
            include.launch_arguments,
            context,
            passed_arguments,
        )
    except ValidationError as e:
        filename, lineno = include.__location__
        raise ValidationError(f"Failed to include launch at {filename}:{lineno}") from e


def validate_source(
    source: launch.LaunchDescriptionSource,
    arguments: Iterable[Tuple[SomeSubstitutionsType, SomeSubstitutionsType]],
    context: launch.LaunchContext,
    passed_arguments: list[str],
) -> None:
    # Add new arguments to the context: resolve argument values in context and set them as launch configurations.
    # Note: this means that arguments passed to a launch file are visible in the parent and sibling launch files...
    resolved_arguments: list[str] = []
    for argument in arguments:
        argument_name = perform_all_substitutions(context, argument[0])
        resolved_arguments.append(argument_name)
        argument_value = perform_all_substitutions(context, argument[1])
        context.launch_configurations[argument_name] = argument_value

    try:
        description = source.get_launch_description(context)
    except FileNotFoundError as e:
        raise ValidationError(f"Failed to open the included launch file: {source.location}") from e

    try:
        # Validate sub-launch description using only the resolved arguments, which are explicitly passed to it and must be declared there.
        validate_launch_description(description, resolved_arguments, context)
    except ValidationError as e:
        raise ValidationError("Failed to process {}".format(source.location)) from e

    # Keep track of passed arguments: resolved_arguments now contain all arguments defined in the
    # included launch descriptions, and appending it to passed_arguments allows us to recursively
    # pass them up the tree.
    passed_arguments += resolved_arguments


def validate_launch_description(
    description: launch.LaunchDescription,
    argument_names: list[str],
    context: launch.LaunchContext,
) -> None:
    defined_arguments: list[str] = []

    for entity in description.entities:
        # NB: this will recurse into groups and includes, appending to defined_arguments as needed.
        # Thus at the end of this loop, defined_arguments will contain all arguments defined in
        # this launch description and any included launch descriptions.
        validate_entity(entity, context, defined_arguments)

        # Verify that arguments are not defined twice in the same launch description tree
        if isinstance(entity, launch.actions.DeclareLaunchArgument):
            if entity.name in defined_arguments:
                file, line = entity.__location__
                raise ValidationError(
                    f"Argument {entity.name} was defined twice. Second definition on {file}:{line}"
                )
            defined_arguments.append(entity.name)

    remainder_arguments = set(argument_names).difference(set(defined_arguments))

    if remainder_arguments:
        # We have arguments left over!
        raise ValidationError(
            f"Arguments {remainder_arguments} were passed to this launch description, "
            "but do not have a corresponding DeclareLaunchArgument"
        )

    argument_names.extend(defined_arguments)


def validate_group(
    group: launch.actions.GroupAction, context: launch.LaunchContext, passed_arguments: list[str]
) -> None:
    # Note: describe_sub_entities will "expand" the action, including potential arguments but
    # will also introduce a pair of push / pop launch configurations to protect the local
    # context, so no need to do it manually here
    for entity in group.get_sub_entities():
        validate_entity(entity, context, passed_arguments)


def validate_push_launch_config(
    push: launch.actions.PushLaunchConfigurations, context: launch.LaunchContext, *_: Any
) -> None:
    push.execute(context)


def validate_pop_launch_config(
    pop: launch.actions.PushLaunchConfigurations, context: launch.LaunchContext, *_: Any
) -> None:
    pop.execute(context)


def validate_argument(
    argument: launch.actions.DeclareLaunchArgument, context: launch.LaunchContext, *_: Any
) -> None:
    # This will raise if an argument without default value is not present in the context
    try:
        argument.execute(context)
    except RuntimeError as e:
        file, line = argument.__location__
        raise ValidationError(str(e) + f" In {file}:{line}") from None


def validate_set_config(
    set_config: launch.actions.SetLaunchConfiguration, context: launch.LaunchContext, *_: Any
) -> None:
    try:
        set_config.execute(context)
    except RuntimeError as e:
        file, line = set_config.__location__
        raise ValidationError(str(e) + f" In {file}:{line}") from None


def validate_condition(action: launch.action.Action, context: launch.LaunchContext) -> bool:
    condition = action.condition
    if condition is None:
        return True

    try:
        return cast(bool, condition.evaluate(context))
    except RuntimeError as e:
        file, line = action.__location__
        raise ValidationError(
            str(e) + f" In the condition of {action.describe()} at {file}:{line}"
        ) from None


def validate_timer(
    timer: launch.actions.TimerAction, context: launch.LaunchContext, passed_arguments: list[str]
) -> None:
    try:
        period = perform_typed_substitution(context, timer.period, float)
    except RuntimeError as e:
        file, line = timer.__location__
        raise ValidationError(str(e) + f" at {file}:{line}") from None

    if period < 0:
        file, line = timer.__location__
        raise ValidationError(
            f"Period of TimerAction should be positive but got {period} at {file}:{line}"
        )

    for action in timer.actions:
        validate_entity(action, context, passed_arguments)


def validate_opaque_function(
    opaque_func: launch.actions.OpaqueFunction,
    context: launch.LaunchContext,
    passed_arguments: list[str],
) -> None:
    try:
        actions = opaque_func.execute(context)
    except Exception as e:
        file, line = opaque_func.__location__
        raise ValidationError(f"Failed to process OpaqueFunction at {file}:{line}") from e

    if actions is not None:
        for action in actions:
            validate_entity(action, context, passed_arguments)


_validate_launch_actions = OrderedDict(
    [
        (launch.actions.DeclareLaunchArgument, validate_argument),
        (launch_ros.actions.Node, validate_node),
        (launch.actions.SetLaunchConfiguration, validate_set_config),
        (launch.actions.PopLaunchConfigurations, validate_pop_launch_config),
        (launch.actions.PushLaunchConfigurations, validate_push_launch_config),
        (launch.actions.IncludeLaunchDescription, validate_source_action),
        (launch.actions.GroupAction, validate_group),
        (launch.actions.TimerAction, validate_timer),
        (launch.actions.OpaqueFunction, validate_opaque_function),
    ]
)


def validate_entity(
    entity: launch.action.Action, context: launch.LaunchContext, passed_arguments: list[str]
) -> None:
    # All types can have a condition, so validate it for every entity
    if validate_condition(entity, context):
        for cls, validation_func in _validate_launch_actions.items():
            if isinstance(entity, cls):
                return cast(None, validation_func(entity, context, passed_arguments))  # type: ignore[operator]
        logger.warning("No linter implemented for launch entity of type %s", type(entity))
    else:
        logger.info("Skipping %s because its condition evaluated to False", entity)


def register_init_hooks() -> None:
    visited_cls: list[type] = []
    for cls in _validate_launch_actions.keys():
        for base_cls in visited_cls:
            if issubclass(cls, base_cls):
                raise RuntimeError(
                    f"{cls} comes after {base_cls} in launch action keys, that's likely a programming mistake"
                )
        register_init(cls)
        visited_cls.append(cls)
