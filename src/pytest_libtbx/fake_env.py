# coding: utf-8
from __future__ import absolute_import, division, print_function
import sys
from six.moves import StringIO


class CustomRuntestsEnvironment:
    """Fakes a minor libtbx environment for loading run_tests"""

    def __init__(self):
        self.tests = []
        self._run_tests = None
        self._discover = None
        self._stdout = None
        self.ran_discover = False

    def __enter__(self):
        # Inline import so we only try if collecting a libtbx file
        import libtbx.test_utils.pytest

        # Back up the functions we're monkeypatching
        self._run_tests = (libtbx.test_utils, libtbx.test_utils.run_tests)
        self._discover = (libtbx.test_utils.pytest, libtbx.test_utils.pytest.discover)
        self._stdout = sys.stdout

        # Replace the discover and run_tests functions
        libtbx.test_utils.run_tests = self.run_tests
        libtbx.test_utils.pytest.discover = self.pytest_discover

        # And the stdout, for things like mmtbx that are verbose
        sys.stdout = StringIO()

        return self

    def __exit__(self, type, value, traceback):
        # Restore the functions back to their original locations
        self._run_tests[0].run_tests = self._run_tests[1]
        self._discover[0].discover = self._discover[1]
        sys.stdout = self._stdout

    def pytest_discover(self, module=None, pytestargs=None):
        """Method to be used to override the libtbx pytest discovery.
        This is so that we don't recursively use pytest to search for more tests
        whilst using pytest to search for tests."""
        assert module is None
        assert pytestargs is None
        self.ran_discover = True
        return []

    def run_tests(self, build_dir, dist_dir, test_list):
        """Replaces the actual test runner with a method to accumulate tests"""
        raise RuntimeError("Don't understand cases when this is run")
        self.tests.extend(test_list)
