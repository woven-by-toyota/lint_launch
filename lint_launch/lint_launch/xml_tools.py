# Copyright 2026 Toyota Motor Corporation

import functools
import sys
from launch.frontend.expose import instantiate_action
import launch_xml
import launch
from launch_xml.entity import Entity
from launch_xml.parser import Parser
import xml.etree.ElementTree as ET


class LineNumberingParser(ET.XMLParser):
    def __init__(self, file_name: str | None):
        super().__init__()
        self.file_name = file_name

    def _start(self, *args, **kwargs):
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


@functools.wraps(instantiate_action)
def my_instantiation(entity, parser):
    action = instantiate_action(entity, parser)
    if hasattr(entity, "_Entity__xml_element"):
        action.__location__ = (
            entity._Entity__xml_element._file_name,
            entity._Entity__xml_element._start_line_number,
        )
    return action


def register_xml_hooks():
    launch_xml.parser.Parser.load = classmethod(load)
    launch.frontend.parser.instantiate_action = my_instantiation
