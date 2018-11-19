# -*- coding: utf-8 -*-

import os
import pytest
import logging
import importlib
import py.path

from .fake_env import CustomRuntestsEnvironment

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# module paths with libtbx tests, but are not pytest-compatible
_tbx_pytest_ignore_roots = []
# Dirs that have already been checked for a run_tests.py
_collected_dirs = set()
# run_tests.py that have been found and read but not 'collected' yet
_precollected_runtests = {}

# XFEL is an odd case - it has no test runner but is not pytest compatible.
# Ignore it for collection by default, unless it magically gets a run_tests
# in the future
try:
    import xfel
except ImportError:
    pass
else:
    xfel_root = py.path.local(xfel.__file__).dirpath()
    if not (xfel_root / "run_tests.py").isfile():
        _tbx_pytest_ignore_roots.append(xfel_root)


def _read_run_tests(path):
    """
    Read a libtbx run_tests file and return the module object

    Arguments:
        path (py.path): The run_tests.py file to read

    Returns:
        ModuleType: The run_tests module
    """
    # Don't import this until we know we need it
    import libtbx.load_env

    _tbx_pytest_ignore_roots.append(path.dirpath())

    # Guess the module import path from the location of this file
    test_module = path.dirpath().basename
    # We must be directly inside the root of a configured module.
    # If this module isn't configured, then we don't want to run tests.
    if not libtbx.env.has_module(test_module):
        return
    run_tests_module = test_module + "." + path.purebasename

    # Import, but intercept some of it's registration calls
    with CustomRuntestsEnvironment() as env:
        run_tests = importlib.import_module(run_tests_module)

    # If we didn't run discover, we can't trust that files are named properly
    if not env.ran_discover:
        _tbx_pytest_ignore_roots.append(path.dirpath())

    return run_tests


class LibTBXRunTestsFile(pytest.File):
    """A Collector to collect tests from run_tests.py"""

    def __init__(self, path, run_tests, parent):
        super(LibTBXRunTestsFile, self).__init__(path, parent)
        self._run_tests = run_tests
        assert run_tests

    def collect(self):
        import libtbx

        # Now collect each test in this file - if it has a test list
        for test in self._run_tests.__dict__.get("tst_list", []):
            markers = []
            if isinstance(test, basestring):
                testfile = test
                testparams = []
                testname = "main"
            elif callable(test):
                # A very minimal number of run_tests embed the functions
                markers.append(
                    pytest.mark.skip(
                        "Callable inside run_tests.py not supported in pytest bridge"
                    )
                )
                testfile = "."
                testparams = []
                testname = "inline"
            else:
                testfile = test[0]
                testparams = [str(s) for s in test[1:]]
                testname = "_".join(str(p) for p in testparams)

            modfile = py.path.local(self._run_tests.__file__)
            full_command = testfile.replace("$D", modfile.dirname).replace(
                "$B", libtbx.env.under_build(modfile.dirpath().basename)
            )
            shortpath = testfile.replace("$D/", "").replace("$B/", "build/")
            pytest_file_object = pytest.File(shortpath, self.parent)
            logger.info("Found libtbx test %s::%s", shortpath, testname)
            test = LibTBXTest(testname, pytest_file_object, full_command, testparams)
            for marker in markers:
                test.add_marker(marker)
            yield test

        # return []


class LibTBXTest(pytest.Item):
    def __init__(self, name, parent, test_command, test_parameters):
        super(LibTBXTest, self).__init__(name, parent)
        self.test_cmd = test_command
        if test_command.endswith(".py"):
            self.test_cmd = 'libtbx.python "%s"' % self.test_cmd
        self.test_parms = test_parameters
        self.full_cmd = " ".join([self.test_cmd] + self.test_parms)
        # Not sure about these?
        # if not hasattr(self, 'module'):
        #     self.module = None
        # if not hasattr(self, '_fixtureinfo'):
        #     self._fixtureinfo = self.session._fixturemanager.getfixtureinfo(self, self.runtest, self)


def pytest_collect_file(path, parent):
    # Look for a file in this same directory called run_tests.py that
    # hasn't been checked before (or a parent directory - only one per tree)
    dirpath = path.dirpath()
    if not dirpath in _collected_dirs:
        _collected_dirs.add(dirpath)
        run_tests = dirpath / "run_tests.py"
        if path == run_tests or run_tests.isfile():
            logger.info("Found %s, caching", run_tests)
            _precollected_runtests[run_tests] = _read_run_tests(run_tests)
        _collected_dirs.add(dirpath)

    # Now, do the normal collection actions
    logger.info("   pytest_collect_file(%s, %s):", path, parent)
    if path.basename == "run_tests.py":
        logger.debug("Collecting libtbx file %s", path)
        # We *must* have seen this file before, even if it was immediately above
        run_tests = _precollected_runtests.pop(path)
        if run_tests is not None:
            return LibTBXRunTestsFile(path, run_tests, parent)


def pytest_collect_directory(path, parent):
    logger.info("pytest_collect_directory(%s, %s):", path, parent)


def pytest_ignore_collect(path, config):
    # import pdb
    # pdb.set_trace()
    logger.info("pytest_ignore_collect(%s, %s):", path, config)
    moduleinit = path.dirpath() / "__init__.py"
    if path.basename == "run_tests.py" or path == moduleinit:
        return False
    for module in _tbx_pytest_ignore_roots:
        if path.common(module) == module:
            logger.info("   Ignoring tbx non-pytest path")
            return True


def pytest_collection_modifyitems(session, config, items):
    # logger.info("pytest_collection_modifyitems(%s, %s, %s):", session, config, items)
    # Called after collections, let's clean up our memory usage
    _collected_dirs = set()
    # # We should have collected everything that we opened
    # if _precollected_runtests:
    #     for runt in _precollected_runtests:
    #         logger.warning("Unprocessed run_tests: %s", runt)
    assert not _precollected_runtests


# def pytest_collectreport(report):
#     logger.info("pytest_collectreport(%s)", report)
