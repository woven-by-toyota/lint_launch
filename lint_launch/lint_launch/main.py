# Copyright 2026 Toyota Motor Corporation
import argparse
import logging

# Disable C-extension to allow customization of the parser
# This must be done before importing launch_xml or elementTree
import sys

sys.modules["_elementtree"] = None
from collections.abc import Iterable
from pathlib import Path

import launch

from lint_launch.test_output import write_failure, write_success
from lint_launch.validation_error import ValidationError, custom_exception_format
from lint_launch.validators import register_init_hooks, validate_source
from lint_launch.xml_tools import register_xml_hooks

logger = logging.getLogger(__name__)


def do_lint(
    filepath: Path,
    launch_arguments: Iterable[tuple[str, str]],
    junit_xml: str | None = None,
    exit_code: bool = False,
) -> None:
    source = launch.launch_description_sources.AnyLaunchDescriptionSource(filepath.as_posix())

    file_name = filepath.stem

    context = launch.LaunchContext()

    try:
        validate_source(source, launch_arguments, context, [])
    except Exception as e:
        if isinstance(e, ValidationError):
            error_contents = custom_exception_format(e)
            logger.critical(error_contents)
        else:
            error_contents = str(e)
            logger.exception(e)
        if junit_xml is not None:
            write_failure(junit_xml, file_name, error_contents)
        if exit_code:
            sys.exit(1)
        return
    else:
        if junit_xml is not None:
            write_success(junit_xml, file_name)


def main() -> None:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="[%(levelname)s] [%(asctime)s] %(message)s"))
    logger.addHandler(handler)

    register_init_hooks()

    try:
        import launch_xml

        register_xml_hooks()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Validate a launch file")
    parser.add_argument("file", type=Path, help="Launch file to be tested")
    parser.add_argument("--junit-xml", help="Output a test report")
    parser.add_argument(
        "--exit-code", action="store_true", help="Reflect the state of the lint in the exit code"
    )
    parser.add_argument("launch_args", nargs="*")

    args = parser.parse_args()

    launch_arguments: list[tuple[str, str]] = []
    for arg in args.launch_args:
        name, value = arg.split(":=")
        launch_arguments.append((name, value))

    do_lint(args.file, launch_arguments, args.junit_xml, args.exit_code)
