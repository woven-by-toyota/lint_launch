# Copyright 2026 Toyota Motor Corporation
# Copyright 2019 Apex.AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#  This file contains modified code from the following open source projects
#  published under the licenses listed below:
#
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

macro(parse_launch_lint_arguments namespace filename)
    cmake_parse_arguments(${namespace} "" "TARGET" "ARGS" ${ARGN})

    set(${namespace}_FILE_NAME NOTFOUND)
    if(IS_ABSOLUTE ${filename})
        set(${namespace}_FILE_NAME ${filename})
    else()
        find_file(
            ${namespace}_FILE_NAME ${filename}
            PATHS ${CMAKE_CURRENT_SOURCE_DIR}
            NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH
        )
        if(NOT ${namespace}_FILE_NAME)
            message(FATAL_ERROR "Can't find launch test file \"${filename}\"")
        endif()
    endif()

    if(NOT ${namespace}_TARGET)
        # strip PROJECT_SOURCE_DIR and PROJECT_BINARY_DIR from absolute filename to get unique test
        # name (as rostest does it internally)
        set(${namespace}_TARGET ${${namespace}_FILE_NAME})
        rostest__strip_prefix(${namespace}_TARGET "${PROJECT_SOURCE_DIR}/")
        rostest__strip_prefix(${namespace}_TARGET "${PROJECT_BINARY_DIR}/")
        string(REPLACE "/" "_" ${namespace}_TARGET ${${namespace}_TARGET})


        string(PREPEND ${namespace}_TARGET "lint_")

        if(${namespace}_ARGS)
            list(JOIN ${namespace}_ARGS "_" joined_args)
            string(REPLACE ":=" "_" joined_args "${joined_args}")
            string(APPEND ${namespace}_TARGET "_${joined_args}")
        endif()
    endif()

    set(${namespace}_RESULT_FILE
        "${AMENT_TEST_RESULTS_DIR}/${PROJECT_NAME}/${${namespace}_TARGET}.xunit.xml"
    )
endmacro()

macro(rostest__strip_prefix var prefix)
    string(LENGTH ${prefix} prefix_length)
    string(LENGTH ${${var}} var_length)
    if(${var_length} GREATER ${prefix_length})
        string(SUBSTRING "${${var}}" 0 ${prefix_length} var_prefix)
        if("${var_prefix}" STREQUAL "${prefix}")
            # passing length -1 does not work for CMake < 2.8.5
            # http://public.kitware.com/Bug/view.php?id=10740
            string(LENGTH "${${var}}" _rest)
            math(EXPR _rest "${_rest} - ${prefix_length}")
            string(SUBSTRING "${${var}}" ${prefix_length} ${_rest} ${var})
        endif()
    endif()
endmacro()

# Add a file to be linted: will be ran as part of colcon test
# ~~~
# :param filename: The launch file to be linted
# :type filename: string
# :param TARGET: The test target name (optional)
# :type TARGET: string
# :param ARGS: launch arguments to be passed to the test
# :type ARGS: string
# ~~~
function(add_launch_lint filename)
    # Convert filename to CMake path before calling macro to avoid problems with backslashes in the
    # filename string.
    file(TO_CMAKE_PATH "${filename}" filename)
    parse_launch_lint_arguments(_launch_lint ${filename} ${ARGN})

    set(cmd
        "lint-launch"
        "${_launch_lint_FILE_NAME}" "${_launch_lint_ARGS}" "--junit-xml"
        "${_launch_lint_RESULT_FILE}"
    )

    ament_add_test(
        "${_launch_lint_TARGET}"
        COMMAND
        ${cmd}
        OUTPUT_FILE
        "${CMAKE_BINARY_DIR}/launch_lint/${_launch_lint_TARGET}.txt"
        RESULT_FILE
        "${_launch_lint_RESULT_FILE}"
        TIMEOUT
        10.0
        ${_launch_test_UNPARSED_ARGUMENTS}
    )
endfunction()
