from __future__ import annotations

import sys
from collections import defaultdict
from types import ModuleType

import py.path
import pytest

pytest_plugins = "pytester"


def _build_raiser(message):
    """Builds a callable that raises if called with a custom message"""

    def _raise(*args, **kwargs):
        raise RuntimeError(message)

    return _raise


class FakeLibTBXModule(object):
    def __init__(self, name, path):
        self.name = name
        self.dist_paths = [path, None]


class FakeLibTBX(object):
    """Creates a fake libtbx environment with physical structure.

    This allows you to simulate a libtbx environment whilst having on-disk
    behaviour for searching for tests. Behaves like a libtbx.env object,
    with extra functionality to manupulate the environment.
    """

    # Save previous environments, as a stack for reentrancy
    _previous_modules = defaultdict(list)
    # _previous_libtbx_load_env = []

    def __init__(self, dist_path):
        self._dist_path = py.path.local(dist_path)
        self._python_modules = {}

        # The plugin itself uses libtbx and load_env
        libtbx = self._add_import("libtbx")
        libtbx.env = self
        libtbx.load_env = self._add_import("libtbx.load_env")

        # Running collectors replaces these functions that run_tests use
        libtbx.test_utils = self._add_import("libtbx.test_utils")
        libtbx.test_utils.pytest = self._add_import("libtbx.test_utils.pytest")
        libtbx.test_utils.run_tests = _build_raiser(
            "run_tests should never be called from pytest-libtbx tests"
        )
        libtbx.test_utils.pytest.discover = _build_raiser(
            "discover should never be called from pytest-libtbx tests"
        )
        self._libtbx = libtbx

        self.module_list = []
        self.module_dist_paths = {}
        self.add_module("libtbx")

    def _add_import(self, name):
        """Create a python module and adds to the list to replace."""
        module = ModuleType(name)
        module.__file__ = name + ".py"
        self._python_modules[name] = module
        return module

    def __enter__(self):
        # Save any existing module, then insert our fake one
        for name, module in self._python_modules.items():
            FakeLibTBX._previous_modules[name].append(sys.modules.get(name, None))
            sys.modules[name] = module

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Restore any previous modules
        for name in self._previous_modules:
            prev_mod = self._previous_modules[name].pop()
            if prev_mod:
                sys.modules[name] = prev_mod
            else:
                del sys.modules[name]

    def add_module(self, name, init=True):
        # type: (str) -> py.path.local
        """ "Adds a libtbx module to the environment paths.

        Args:
            name: The module name. A path will be created.

        Returns:
            The dist path for the new module.
        """
        path = self._dist_path / name
        if not path.check():
            path.mkdir()
        if init:
            (path / "__init__.py").ensure(file=True)
        self.module_list.append(FakeLibTBXModule(name, path))
        self.module_dist_paths[name] = path
        return path

    def dist_path(self, name):
        return self.module_dist_paths[name]

    def under_build(self, name):
        build_path = self._dist_path / "_build" / name
        build_path.ensure(dir=True)
        return build_path

    def has_module(self, name):
        return name in self.module_dist_paths


# _load_env_template = """
# import libtbx
# import py.path

# module_list_file = py.path.local(__file__).dirpath() / "modules.list"


# class module(object):
#     def __init__(self, path):
#         path = py.path.local(path.strip())
#         self.name = path.basename
#         self.dist_paths = [path, None]


# class env(object):
#     def __init__(self):
#         self._root = py.path.local(__file__).dirpath().dirpath()
#         self.module_list = [
#             module(x) for x in module_list_file.readlines() if x.strip()
#         ]
#         self.module_dist_paths = {x.name: x.dist_paths[0] for x in self.module_list}

#     def dist_path(self, module):
#         return self.module_dist_paths[module]

#     def under_build(self, name):
#         build_path = self._root / "_build" / name
#         build_path.ensure(dir=True)
#         return build_path

#     def has_module(self, name):
#         return name in self.module_dist_paths


# libtbx.env = env()
# """

# def FakeLibTBX(object):
#     def __init__(self, path):
#         self._root = py.path.local(path)
#         libtbx = self._root / "libtbx"
#         libtbx.mkdir()
#         (libtbx / "__init__.py").ensure(file=True)
#         with (libtbx / "load_env.py").ensure(file=True).open() as f:
#             f.write(_load_env_template)
#         with(libtbx/"modules.list").open("w") as f:
#             f.write(str(libtbx)+"\n")


@pytest.fixture
def libtbx(testdir):
    """Create a fake libtbx environment and return it"""
    with FakeLibTBX(testdir.tmpdir) as libtbx:
        yield libtbx
