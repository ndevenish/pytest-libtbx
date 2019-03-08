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
import _pytest.fixtures as fixtures

# For now, relax the constraint on having a valid environment
import libtbx.load_env
import libtbx.path

from .fake_env import CustomRuntestsEnvironment

try:
    from typing import Set
except ImportError:
    pass

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Module paths we are deliberately ignoring
_tbx_pytest_ignore_roots = set()  # type: Set[py.path.local]
# Dirs that have already been checked for a run_tests.py
_collected_dirs = set()
# run_tests.py that have been found and read but not 'collected' yet
_precollected_runtests = {}
# Paths to every configured libtbx module so we don't try to run unused modules
_valid_libtbx_module_paths = set()


def pytest_sessionstart(session):
    """Start the pytest session.

    Use this to introspect libtbx and work out the locations/exclusions.
    """
    # Work out all the libtbx modules
    for module in libtbx.env.module_list:
        for path in [x for x in module.dist_paths if x is not None]:
            if isinstance(path, libtbx.path.path_mixin):
                path = abs(path)
            _valid_libtbx_module_paths.add(py.path.local(path))
    valid_modules = {x.name for x in libtbx.env.module_list}

    # xfel doesn't have a run_tests.py but does have pytest-named-style tests
    # Ignore it, unless a run_tests.py is added.
    try:
        xfel_root = py.path.local(libtbx.env.dist_path("xfel"))
    except KeyError:
        xfel_root = py.path.local(libtbx.env.dist_path("libtbx")).parent / "xfel"
    if not (xfel_root / "run_tests.py").isfile():
        _tbx_pytest_ignore_roots.add(xfel_root)
        valid_modules.discard("xfel")

    # Deliberately ignore the 'boost' folder in the modules path because
    # we know this has files which confuse pytest.
    modules_root = py.path.local(libtbx.env.dist_path("libtbx")).dirpath().dirpath()
    boost_root = modules_root / "boost"
    _tbx_pytest_ignore_roots.add(boost_root)
    _valid_libtbx_module_paths.discard(boost_root)
    valid_modules.discard("boost")

    logger.info("Allowed libtbx modules: %s, ", ", ".join(sorted(valid_modules)))


# def _attempt_ignore_module(name, unless_runtests=False):
#     """
#     Try to import a module, and add to the collection ignore list.

#     Arguments:
#         name (str): The module name to try importing
#         unless_runtests (bool): If True, look for a run_tests.py and allow
#                                 the module to be scanned if present.
#     """
#     try:
#         module = importlib.import_module(name)
#     except ImportError:
#         pass
#     else:
#         root_path = py.path.local(module.__file__).dirpath()
#         if not (unless_runtests and (root_path / "run_tests.py").isfile()):
#             _tbx_pytest_ignore_roots.add(root_path)


# XFEL has no test runner, but has non-pytest pytest-named tests.
# Ignore it for collection by default, unless it gets a run_tests
# _attempt_ignore_module("xfel", unless_runtests=True)


def _read_run_tests(path):
    """
    Read a libtbx run_tests file and return the module object

    Arguments:
        path (py.path): The run_tests.py file to read

    Returns:
        ModuleType: The run_tests module, or None
    """
    # Don't import this until we know we need it
    import libtbx.load_env

    # _tbx_pytest_ignore_roots.append(path.dirpath())

    # Guess the module import path from the location of this file
    test_module = path.dirpath().basename
    # We must be directly inside the root of a configured module.
    # If this module isn't configured, then we don't want to run tests.
    module_configured = libtbx.env.has_module(test_module)
    module_import = test_module + "." + path.purebasename

    # TODO: Possibly replace importing with
    # run_tests = path.pyimport()
    # package_path = path.pypkgpath()

    try:
        # Import, but intercept some of it's registration calls
        with CustomRuntestsEnvironment() as env:
            run_tests = importlib.import_module(module_import)
    except ImportError:
        # If this wasn't configured, ignore errors
        if not module_configured:
            run_tests = None

    # If we didn't run discover, we can't trust that files are named properly.
    # We can probably extract this information even if not configured
    if not env.ran_discover or not module_configured:
        logger.info("%s didn't run discover so ignoring for collection", path)
        _tbx_pytest_ignore_roots.add(path.dirpath())

    # if we aren't configured, we don't want to return a module at all
    if not module_configured:
        return None

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

    # Accumulate markers to apply to the test
    markers = [pytest.mark.usefixtures("tmpdir")]

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

    # Handle hard-coded behaviour

    # Hard-coded ignore tests
    _test_utils_path = (
        py.path.local(libtbx.env.dist_path("libtbx")) / "test_utils" / "__init__.py"
    )
    custom_test_marks = [
        (
            _test_utils_path,
            pytest.mark.xfail(
                reason="libtbx/test_utils/__init__.py, insanely, asserts on stack trace length"
            ),
        ),
        (
            py.path.local(libtbx.env.dist_path("dials_regression")),
            pytest.mark.skip("dials_regression has no tests"),
        ),
    ]
    for path, reason in custom_test_marks:
        if path.common(py.path.local(full_command)) == path:
            markers.append(reason)

    # Skip anything in mmtbx if no monomer library present
    if libtbx.env.has_module("mmtbx"):
        lib = py.path.local(libtbx.env.dist_path("mmtbx"))
        has_env = "MMTBX_CCP4_MONOMER_LIB" in os.environ or "CLIBD_MON" in os.environ
        if py.path.local(full_command).common(lib) == lib and not has_env:
            markers.append(
                pytest.mark.skip(
                    reason="No monomer library - set MMTBX_CCP4_MONOMER_LIB or CLIBD_MON"
                )
            )

    # Generate a short path to use as the name
    # shortpath = testfile.replace("$D/", module.basename + "/").replace("$B/", module.basename+"/build/")
    shortpath = testfile.replace("$D/", "").replace("$B/", "build/")
    # Create a file parent object
    pytest_file_object = pytest.File(shortpath, parent)
    logger.info("Found libtbx test %s::%s", shortpath, testname)

    test = LibTBXTest(
        testname, pytest_file_object, full_command, testparams, markers=markers
    )

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
            yield test


class LibTBXTestException(Exception):
    """Custom exception for error reporting."""


class LibTBXTest(pytest.Item):
    def __init__(self, name, parent, test_command, test_parameters, markers=None):
        super(LibTBXTest, self).__init__(name, parent)
        self.test_cmd = test_command

        # Build the full list of arguments
        # test_parameters is a list, but this is pointless because the
        # tst_list in a run_tests can contain items that need to be split -
        # so it needs to be joined and re-shell-split anyway.
        self.test_params = shlex.split(" ".join(test_parameters))
        self.full_cmd = [self.test_cmd] + self.test_params

        for marker in markers:
            self.add_marker(marker)

        # Handle fixtures from this test/for markers
        self._fixtureinfo = self.session._fixturemanager.getfixtureinfo(
            self, self.runtest, self
        )

    def runtest(self):
        "Called by pytest to run the actual test"

        # Build the tmpdir fixture request
        self.funcargs = {}
        request = fixtures.FixtureRequest(self)
        request._fillfixtures()
        # Switch to this function
        self.funcargs["tmpdir"].chdir()

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
    # if ".py" in path.strpath:
    print("Collecting " + str(path))

    # Look for a file in this same directory called run_tests.py that
    # hasn't been checked before (or a parent directory - only one per tree)
    dirpath = path.dirpath()
    if dirpath not in _collected_dirs:
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
    # (Appears to be: Never ignore __init__.py or run_tests.py)
    moduleinit = path.dirpath() / "__init__.py"
    if path.basename == "run_tests.py" or path == moduleinit:
        return False

    # Check if we're in a subdirectory that we want to disable collection
    for module in _tbx_pytest_ignore_roots:
        if path.common(module) == module:
            return True


def pytest_collection_modifyitems(session, config, items):
    # Called after collections, let's clean up our memory usage
    global _collected_dirs
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
