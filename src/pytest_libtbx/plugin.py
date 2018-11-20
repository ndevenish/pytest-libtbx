# -*- coding: utf-8 -*-

import os
import sys
import pytest
import logging
import importlib
import py.path
import six
import procrunner
import runpy
import shlex

from .fake_env import CustomRuntestsEnvironment

# logging.basicConfig(level=logging.DEBUG)
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


def _test_from_list_entry(entry, runtests_file, parent):
    """
    Create a LibTBXTest entry from a tst_list entry

    Arguments:
        entry (str or Iterable or Callable): The entry in the tst_list. This can
            be a string filename, a list of filename and arguments, or an
            inline function call (which will be skipped).
        file (py.path.local):   The run_tests filename that this entry was from

        parent (pytest.Node):   The parent node for the test

    Returns:
        LibTBXTest: The pytest test object to execute
    """
    import libtbx.load_env  # Inline so that we don't import if not using

    # In case we decide to apply any markers whilst building
    markers = []

    # Extract the file, parameter information
    if isinstance(entry, six.string_types):
        testfile = entry
        testparams = []
        testname = "main"
    elif hasattr(entry, "__iter__"):
        testfile = entry[0]
        testparams = [str(x) for x in entry[1:]]
        testname = "_".join(str(p) for p in testparams)
    elif callable(entry):
        # Only a couple of these cases exist and awkward enough that we
        # can afford to skip them
        markers.append(
            pytest.mark.skip(
                "Callable inside run_tests.py not supported in pytest bridge"
            )
        )
        testfile = runtests_file.strpath
        testparams = []
        testname = "inline"

    # Expand the test file into a real path
    module = runtests_file.dirpath()
    # Convert any placeholder values to absolute paths
    full_command = testfile.replace("$D", module.strpath).replace(
        "$B", libtbx.env.under_build(module.basename)
    )

    # Skip anything in mmtbx if no monomer library present
    if libtbx.env.has_module("mmtbx"):
        lib = py.path.local(libtbx.env.dist_path("mmtbx"))
        has_env = "MMTBX_CCP4_MONOMER_LIB" in os.environ or "CLIBD_MON" in os.environ
        if py.path.local(full_command).common(lib) == lib and not has_env:
            markers.append(
                pytest.mark.skip(
                    "No monomer library - set MMTBX_CCP4_MONOMER_LIB or CLIBD_MON"
                )
            )

    # Generate a short path to use as the name
    shortpath = testfile.replace("$D/", "").replace("$B/", "build/")
    # Create a file parent object
    pytest_file_object = pytest.File(shortpath, parent)
    logger.info("Found libtbx test %s::%s", shortpath, testname)
    test = LibTBXTest(testname, pytest_file_object, full_command, testparams)
    # Add any markers we might have wanted
    for marker in markers:
        test.add_marker(marker)

    return test


class LibTBXRunTestsFile(pytest.File):
    """A Collector to collect tests from run_tests.py"""

    def __init__(self, path, run_tests, parent):
        super(LibTBXRunTestsFile, self).__init__(path, parent)
        self._run_tests = run_tests
        assert run_tests

    def collect(self):
        # Collect each test in this file - if it has a test list
        for test in self._run_tests.__dict__.get("tst_list", []):
            yield _test_from_list_entry(test, self.fspath, self.parent)

        # Now, handle tst_list_slow
        for test in self._run_tests.__dict__.get("tst_list_slow", []):
            test = _test_from_list_entry(test, self.fspath, self.parent)
            test.add_marker(pytest.mark.regression)
            logger.debug("test %s is a slow test", test)


class LibTBXTestException(Exception):
    """Custom exception for error reporting."""


class LibTBXTest(pytest.Item):
    def __init__(self, name, parent, test_command, test_parameters):
        super(LibTBXTest, self).__init__(name, parent)
        self.test_cmd = test_command

        # Build the full list of arguments
        # test_parameters is a list, but this is pointless because the
        # tst_list in a run_tests can contain items that need to be split -
        # so it needs to be joined and re-shell-split anyway.
        self.test_params = shlex.split(" ".join(test_parameters))
        self.full_cmd = [self.test_cmd] + self.test_params

    def runtest(self):
        "Called by pytest to run the actual test"

        if self.test_cmd.endswith(".py"):
            # We are running a python script. Run it in-process for speed
            # Save the old command line arguments
            prior_argv = sys.argv
            # TBX RULE: Tests rely on old relative-import behaviour
            prior_path = list(sys.path)
            dir_path = py.path.local(self.test_cmd).dirname
            try:
                sys.argv = self.full_cmd
                sys.path.insert(0, dir_path)
                runpy.run_path(self.test_cmd, run_name="__main__")
            except SystemExit as e:
                if e.code != 0:
                    raise LibTBXTestException("Script exited with non-zero error code")
            finally:
                sys.argv = prior_argv
                sys.path = prior_path
        else:
            print("Procrunning ", self.test_cmd)
            # Not a python script. Assume that we can run as an external program
            result = procrunner.run(
                self.full_cmd, print_stdout=False, print_stderr=False
            )
            self.add_report_section("call", "stdout", result["stdout"])
            self.add_report_section("call", "stderr", result["stderr"])
            if result["stderr"] or result["exitcode"] != 0:
                raise LibTBXTestException("Script exited with non-zero error code")


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
    if path.basename == "run_tests.py":
        logger.debug("Collecting libtbx file %s", path)
        # We *must* have seen this file before, even if it was immediately above
        run_tests = _precollected_runtests.pop(path)
        if run_tests is not None:
            return LibTBXRunTestsFile(path, run_tests, parent)


def pytest_ignore_collect(path, config):
    # If __init__.py is ignored, the whole module is ignored
    moduleinit = path.dirpath() / "__init__.py"
    if path.basename == "run_tests.py" or path == moduleinit:
        return False
    # Check if we're in a subdirectory that we want to disable collection
    for module in _tbx_pytest_ignore_roots:
        if path.common(module) == module:
            return True


def pytest_collection_modifyitems(session, config, items):
    # Called after collections, let's clean up our memory usage
    _collected_dirs = set()
    # # We should have collected everything that we opened
    assert not _precollected_runtests


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "regression: Mark as a (time-intensive) regression test"
    )


def pytest_addoption(parser):
    """Add '--regression' options to pytest."""
    try:
        parser.addoption(
            "--regression",
            action="store_true",
            default=False,
            help="run (time-intensive) regression tests",
        )
    except ValueError:
        # Thrown in case the command line option is already defined
        pass


def pytest_runtest_setup(item):
    # Check if we want to run regression tests
    if item.get_marker(name="regression"):
        if not item.config.getoption("--regression"):
            pytest.skip("Test only runs with --regression")
