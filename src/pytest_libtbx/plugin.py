# -*- coding: utf-8 -*-

import pytest
import logging

from .fake_libtbx import FakeTBXEnvironment

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _read_libtbx_run_tests(file):
    """
    Read a libtbx run_tests file and extract data

    Arguments:
        file (py.path): The run_tests file to load
    """
    pass

class LibTBXRunTestsFile(pytest.File):
    def collect(self):
        runtests = _read_libtbx_run_tests(self.fspath)
        # Yield each test
        return []

def pytest_collect_file(path, parent):
    if path.basename == "run_tests.py":
        logger.debug("Collecting libtbx file %s", path)
        return LibTBXRunTestsFile(path, parent)
