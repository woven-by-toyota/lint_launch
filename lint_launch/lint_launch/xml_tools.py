# Copyright 2026 Toyota Motor Corporation

import functools
import io
import xml.etree.ElementTree as ET

import launch
import launch_xml
from launch.frontend.entity import Entity
from launch.frontend.expose import instantiate_action
from launch.frontend.parser import Parser
from launch_xml.entity import Entity as XMLEntity
from launch_xml.parser import Parser as XMLParser


class LineNumberingParser(ET.XMLParser):
    def __init__(self, file_name: str | None) -> None:
        super().__init__()
        self.file_name = file_name

    def _start(self, *args, **kwargs) -> ET.Element:
        element = super(self.__class__, self)._start(*args, **kwargs)
        element._file_name = self.file_name
        element._start_line_number = self.parser.CurrentLineNumber
        element._start_column_number = self.parser.CurrentColumnNumber
        element._start_byte_index = self.parser.CurrentByteIndex
        return element


def load(cls: type[XMLParser], file: str | io.TextIOBase) -> tuple[XMLEntity, XMLParser]:
    file_name = getattr(file, "name", None)
    parser = LineNumberingParser(file_name)
    return (XMLEntity(ET.parse(file, parser=parser).getroot()), cls())


@functools.wraps(instantiate_action)
def my_instantiation(entity: Entity, parser: Parser) -> launch.Action:
    action = instantiate_action(entity, parser)
    if hasattr(entity, "_Entity__xml_element"):
        xml_element = entity._Entity__xml_element
        if hasattr(xml_element, "_start_line_number"):
            action.__location__ = (xml_element._file_name, xml_element._start_line_number)
    return action


def register_xml_hooks() -> None:
    launch_xml.parser.Parser.load = classmethod(load)
    launch.frontend.parser.instantiate_action = my_instantiation
