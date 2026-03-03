# Copyright 2026 Toyota Motor Corporation

from typing import Optional


class ValidationError(Exception):
    pass


def custom_exception_format(e: ValidationError) -> str:
    indent = ""
    lines = []
    current_exception: Optional[BaseException] = e
    while current_exception is not None:
        lines.append(indent + str(current_exception))
        current_exception = current_exception.__cause__
        if not indent:
            indent = "|-> "
        else:
            indent = "    " + indent
    return "\n".join(lines)
