
import sys

from types import ModuleType

def new_module(name, doc=None):
    """Create a new module and inject it into sys.modules

    Arguments:
        name (str): Fully qualified name (including parent)

    Returns:
        ModuleType: A module, injected into sys.modules
    """
    m = ModuleType(name, doc)
    m.__file__ = name + '.py'
    sys.modules[name] = m
    return m

class FakeTBXEnvironment():
    """Fakes a minor libtbx environment for loading run_tests"""
    def __init__(self):
        self.tests = []
        self._backup_modules = {}

    def __enter__(self):
        self._backup_modules["libtbx"] = sys.modules.get("libtbx")
        self._backup_modules["libtbx.test_utils"] = sys.modules.get("libtbx.test_utils")
        self._backup_modules["libtbx.test_utils.pytest"] = sys.modules.get("libtbx.test_utils.pytest")

        # Create the miniature libtbx library
        libtbx = new_module("libtbx")
        libtbx.test_utils = new_module("libtbx.test_utils")
        libtbx.test_utils.pytest = new_module("libtbx.test_utils.pytest")

        # Library functions used in these
        libtbx.test_utils.run_tests = self.run_tests
        libtbx.test_utils.pytest.discover = self.pytest_discover

    def __exit__(self, type, value, traceback):
        # Restore the environment from before running this
        for name, module in self._backup_modules:
            if module is None:
                del sys.modules[name]
            else:
                sys.modules[name] = module

    @staticmethod
    def pytest_discover(module, pytestargs=None):
        """Method to be used to override the libtbx pytest discovery.
        This is so that we don't recursively use pytest to search for more tests
        whilst using pytest to search for tests."""
        return []

    def run_tests(self, build_dir, dist_dir, test_list):
        """Replaces the actual test runner with a method to accumulate tests"""
        self.tests.extend(test_list)
