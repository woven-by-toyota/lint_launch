# lint_launch

A linter for ROS2 launch files. It allows you to check your launch files for common issues such as undeclared arguments, references to non-existent nodes, and more. It can be used as a command-line tool or as a Python library.

## Building

Simply clone the repository in your workspace and build it using colcon:

```bash
cd my_ws/src
git clone https://github.com/woven-by-toyota/lint_launch.git
rosdep install --from-paths lint_launch --ignore-src
cd ..
colcon build
```

You can also run tests using either `colcon test` or directly invoking `pytest`.

## Usage

### As a CMake test target

You can depend on the `lint_launch_ament_cmake` package, and use that to define lint targets in your build, just like you would define test targets using `launch_testing_ament_cmake`.
For example, in your `CMakeLists.txt`:
```cmake
if(BUILD_TESTING)
  find_package(lint_launch_ament_cmake REQUIRED)
  add_lint_launch(${PATH_TO_LAUNCH_FILE} ARGS ${ARGUMENTS_TO_PASS_TO_LAUNCH_FILE})
ending()
```

Also don't forget to add the necessary dependencies in your `package.xml`:
```xml
<test_depend>lint_launch</test_depend>
<test_depend>lint_launch_ament_cmake</test_depend>
```

### As a command-line tool

You can use the `lint-launch` command to check your launch files. For example:

```bash
# Inside topic-tools package
lint-launch /opt/ros/jazzy/share/topic_tools/launch/relay.launch
```

Will output nothing and return 0.

If you build a launch file that uses a non-existing executable:
```python
import launch
import launch_ros

def generate_launch_description():
    return launch.LaunchDescription([
      launch_ros.actions.Node(executable='foo', package='bar', name='foobar'),
    ])
```

Then, the linter will point out the error:
```bash
[CRITICAL] [2026-03-05 11:23:44,818] Failed to process $MY_WS/src/lint_launch/foobar.py
|-> "package 'bar' not found, searching: ['$MY_WS/install/lint_launch', '/opt/ros/jazzy']" In /home/herve-audren/dev/ros/lint_launch_ws/src/lint_launch/foobar.py:6
    |-> "package 'bar' not found, searching: ['$MY_WS/install/lint_launch', '/opt/ros/jazzy']"
```

Note how the linter correctly identifies the line number and the file where the error occurs, which is where the action is defined, not where it is used.

You can also pass arguments to the linter, just like you would a regular launch file. For example:
```python
import launch

def generate_launch_description():
    return launch.LaunchDescription([
      launch.actions.DeclareLaunchArgument('foo'),
      launch.actions.LogInfo(msg=launch.substitutions.LaunchConfiguration('foo')),
    ])
```

Then:
```bash
lint-launch foo.py
```

Will point out that you're missing a required argument:
```bash
[ERROR] [launch.actions.declare_launch_argument]: Required launch argument "foo" (description: "no description given") was not provided
[CRITICAL] [2026-03-05 11:33:16,350] Failed to process foo.py
|-> Required launch argument "foo" was not provided. In foo.py:5
```

However, if you provide the argument on the command line, the linter no longer complains:
```bash
lint-launch foo.py foo:=bar
```

Two important flags are provided for better integration with CI systems:
1. `--exit-code` will make the linter return a non-zero exit code if any error is found, which is useful for CI pipelines to fail the build.
2. `--junit-xml` will output the results in JUnit XML format to the file path provided as an argument, which can be used for integration with e.g. colcon test.

### As a Python library

You can also use the linter as a Python library in your own code. For example:
```python
from lint_launch.validators import register_init_hooks, validate_source
from lint_launch.validation_error import ValidationError, custom_exception_format

register_init_hooks()  # This monkey patches the launch system to keep track of the source of each action, allowing us to report accurate error messages with file and line number.
source = some_launch_description_source()
context = launch.LaunchContext()
launch_arguments = []

try:
    validate_source(source, launch_arguments, context, [])
except ValidationError as e:
    print(custom_exception_format(e))
```

This is mostly useful if you'd like to implement your own validators for specific action types that are not covered by the built-in validators, or if you want to integrate the linter into a larger tool that needs to analyze launch files programmatically.

## Design decisions

The linter is designed to catch common issues that can occur in launch files, such as:
1. Required arguments that are not provided to included launch files
2. Extraneous arguments that are provided to included launch files
3. References to non-existent executables on the system
4. Usage of undefined launch configurations

However, not all issues can be caught, and we are still missing coverage for many common launch entities.
If you spot an issue that is not caught by the linter, please open an issue or, better, a pull request with a fix, adding a validator to the list of validators in `lint_launch/validators.py`.
On the other hand, the linter enforces some checks surrounding include rules that are *stricter* than what launch provides by default.
Indeed, launch itself considers all includes to be textual includes, as if the code of the included launch file was pasted where it's included.
Our linter requires you to declare launch arguments explicitly in the included launch file tree before usage, and to explicitly pass all necessary arguments to the included tree.

While the linter will never execute any Executable, it does need to evaluate some parts of the launch system to understand which actions are actually being included:
1. All `condition` attributes are evaluated, and only the actions where the condition evaluates to `True` will be checked
2. Any `OpaqueFunction` will be executed, and the linter will examine all returned actions

This does mean that if you use either of the above to read or modify the state of the system, the linter will execute that code, including any side effect, which can have unpredictable consequences.
