# Copyright 2026 Toyota Motor Corporation

import functools
import inspect
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Text

import launch
from launch.some_substitutions_type import SomeSubstitutionsType
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions

from .validation_error import ValidationError


def register_init(cls: type) -> None:
    # Note mypy warns us (rightly) that we should not directly modify the __init__ method.
    # however, since we need to inject our hook into the constructor of external classes,
    # we don't really have a choice
    func = cls.__init__  # type: ignore

    @functools.wraps(func)
    def my_init(self: object, *args: Any, **kwargs: Optional[Any]) -> None:
        # Get information about the caller of this function
        current_frame = inspect.currentframe()
        # Get information from the parent frame
        if current_frame is not None:
            current_frame = current_frame.f_back

        if current_frame is not None:
            frameinfo = inspect.getframeinfo(current_frame)
            setattr(self, "__location__", (frameinfo.filename, frameinfo.lineno))  # noqa: B010
        func(self, *args, **kwargs)

    cls.__init__ = my_init  # type: ignore


def perform_all_substitutions(
    context: launch.LaunchContext, substitutions: SomeSubstitutionsType
) -> Text:
    try:
        value = perform_substitutions(context, normalize_to_list_of_substitutions(substitutions))
    except launch.substitutions.SubstitutionFailure as e:
        raise ValidationError(str(e)) from None
    # Since launch package does not contain py.typed, mypy considers it untyped. Thus need
    # to force the type annotation here!
    assert isinstance(value, str)
    return value


@contextmanager
def context_stack(context: launch.LaunchContext) -> Iterator[launch.LaunchContext]:
    # Save current launch context
    context._push_launch_configurations()

    try:
        yield context
    finally:
        # Restore previous launch context
        context._pop_launch_configurations()
