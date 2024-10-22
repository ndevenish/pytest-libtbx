#!/usr/bin/env python
from __future__ import annotations

import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-libtbx",
    version="0.1.0",
    author="Nicholas Devenish",
    author_email="ndevenish@gmail.com",
    maintainer="Nicholas Devenish",
    maintainer_email="ndevenish@gmail.com",
    license="BSD-3",
    url="https://github.com/ndevenish/pytest-libtbx",
    description="pytest plugin to load libtbx-style tests",
    long_description=read("README.rst"),
    packages=["pytest_libtbx"],
    package_dir={"": "src"},
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=["pytest>=3.5.0", "procrunner>=0.7.0", "six"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    entry_points={"pytest11": ["libtbx = pytest_libtbx.plugin"]},
)
