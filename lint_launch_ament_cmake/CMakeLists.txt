cmake_minimum_required(VERSION 3.5)

project(lint_launch_ament_cmake)

find_package(ament_cmake REQUIRED)

ament_package(
  CONFIG_EXTRAS "${PROJECT_NAME}-extras.cmake"
)

install(
  DIRECTORY cmake
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  include(cmake/add_launch_lint.cmake)

  add_launch_lint(
    ${CMAKE_CURRENT_SOURCE_DIR}/examples/arg_required.py
    ARGS "foo:=bar"
  )
endif()
