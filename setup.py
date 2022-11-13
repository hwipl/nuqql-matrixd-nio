#!/usr/bin/env python3

"""
nuqql-matrixd-nio setup file
"""

import os
import re
import codecs

from setuptools import setup

# setup parameters
DESCRIPTION = "Matrix client network daemon using matrix-nio"
with open("README.md", 'r', encoding='UTF-8') as f:
    LONG_DESCRIPTION = f.read()
CLASSIFIERS = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]


# setup helpers
def read(*parts):
    """
    Read encoded file
    """

    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, *parts), 'r') as enc_file:
        return enc_file.read()


def find_version(*file_paths):
    """
    Find version in encoded file
    """

    version_file = read(*file_paths)
    version_pattern = r"^VERSION = ['\"]([^'\"]*)['\"]"
    version_match = re.search(version_pattern, version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# run setup
setup(
    name="nuqql-matrixd-nio",
    version=find_version("nuqql_matrixd_nio", "server.py"),
    description=DESCRIPTION,
    license="MIT",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="hwipl",
    author_email="nuqql-matrixd@hwipl.net",
    url="https://github.com/hwipl/nuqql-matrixd-nio",
    packages=["nuqql_matrixd_nio"],
    entry_points={
        "console_scripts": ["nuqql-matrixd-nio = nuqql_matrixd_nio.main:main"]
    },
    classifiers=CLASSIFIERS,
    python_requires='>=3.7',
    install_requires=["nuqql-based~=0.3.0", "matrix-nio[e2e]~=0.20.1"],
)
