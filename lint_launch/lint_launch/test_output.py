# Copyright 2026 Toyota Motor Corporation

template = """
<testsuite tests="1" errors="{}" failures="{}" name="{}">
    <testcase classname="lint_test" name="lint_test">
        {}
    </testcase>
</testsuite>
"""

failure_template = """
        <failure type="LaunchFileFail"> {} </failure>
"""


def write_result(filepath: str, contents: str) -> None:
    with open(filepath, "w") as f:
        f.write(contents)


def write_success(filepath: str, launch_name: str) -> None:
    write_result(filepath, template.format(0, 0, "lint." + launch_name, ""))


def write_failure(filepath: str, launch_name: str, error_contents: str) -> None:
    contents = failure_template.format(error_contents)
    write_result(filepath, template.format(0, 1, "lint." + launch_name, contents))
