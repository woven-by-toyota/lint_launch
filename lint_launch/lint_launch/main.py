# Copyright 2026 Toyota Motor Corporation

import sys
sys.modules['_elementtree'] = None
import xml.etree.ElementTree as ET
import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

import launch

from lint_launch.test_output import write_failure, write_success
from lint_launch.validation_error import ValidationError, custom_exception_format
from lint_launch.validators import register_init_hooks, validate_source

logger = logging.getLogger(__name__)

class LineNumberingParser(ET.XMLParser):
    def __init__(self, file_name: str | None):
        super().__init__()
        self.file_name = file_name

    def _start(self, *args, **kwargs):
        # Here we assume the default XML parser which is expat
        # and copy its element position attributes into output Elements
        element = super(self.__class__, self)._start(*args, **kwargs)
        element._file_name = self.file_name
        element._start_line_number = self.parser.CurrentLineNumber
        element._start_column_number = self.parser.CurrentColumnNumber
        element._start_byte_index = self.parser.CurrentByteIndex
        return element

def load(cls, file):
    file_name = getattr(file, "name", None)
    parser = LineNumberingParser(file_name)
    return (Entity(ET.parse(file, parser=parser).getroot()), cls())

try:
    from launch_xml.parser import Parser
    from launch_xml.entity import Entity
    # Inject file line numbering into the launch_xml parser
    Parser.load = classmethod(load)
    # When isntanciating actions in the parser, inject __location__ to the instance
    from launch.frontend.expose import instantiate_action
    import functools

    @functools.wraps(instantiate_action)
    def my_instantiation(entity, parser):
        action = instantiate_action(entity, parser)
        # Instantiated from launch_xml, so we can get the line number from the XML entity, not python
        if hasattr(entity, "_Entity__xml_element"):
            action.__location__ = (entity._Entity__xml_element._file_name, entity._Entity__xml_element._start_line_number)
        return action

    launch.frontend.parser.instantiate_action = my_instantiation
except ImportError:
    pass

def do_lint(
    filepath: Path,
    launch_arguments: Iterable[Tuple[str, str]],
    junit_xml: Optional[str] = None,
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

    parser = argparse.ArgumentParser(description="Validate a launch file")
    parser.add_argument("file", type=Path, help="Launch file to be tested")
    parser.add_argument("--junit-xml", help="Output a test report")
    parser.add_argument(
        "--exit-code", action="store_true", help="Reflect the state of the lint in the exit code"
    )
    parser.add_argument("launch_args", nargs="*")

    args = parser.parse_args()

    launch_arguments: list[Tuple[str, str]] = []
    for arg in args.launch_args:
        name, value = arg.split(":=")
        launch_arguments.append((name, value))

    do_lint(args.file, launch_arguments, args.junit_xml, args.exit_code)
