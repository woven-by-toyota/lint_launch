#!/usr/bin/env python

# Copyright 2026 Toyota Motor Corporation

from setuptools import find_packages, setup
import xml.etree.ElementTree as ET

package_xml = ET.parse("package.xml").getroot()
package_name = package_xml.find("name").text

setup(
    name=package_name,
    version=package_xml.find("version").text,
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    packages=find_packages(),
    package_data={"lint_launch": ["py.typed"]},
    install_requires=["setuptools"],
    tests_require=["pytest"],
    author=", ".join(a.text for a in package_xml.findall("author")),
    maintainer=package_xml.find("maintainer").text,
    url=package_xml.find("url").text,
    keywords="lint,launch",
    zip_safe=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache-2.0",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries",
    ],
    description="A linter for ros2 launch files.",
    long_description="A linter for ros2 launch files, verifying for common mistakes such as missing arguments, non-existing executables and more.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "lint-launch = lint_launch.main:main",
        ],
    },
)
