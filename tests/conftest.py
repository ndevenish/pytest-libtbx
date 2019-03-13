import sys
from types import ModuleType

import py.path
import pytest

pytest_plugins = "pytester"


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
    _previous_libtbx = []
    _previous_libtbx_load_env = []

    def __init__(self, dist_path):
        self._dist_path = py.path.local(dist_path)
        self._libtbx = ModuleType("libtbx")
        self._libtbx.__file__ = "fake_libtbx.py"
        self._libtbx.load_env = ModuleType("libtbx.load_env")
        self._libtbx.load_env = "fake_libtbx_load_env.py"
        self._libtbx.env = self

        self.module_list = []
        self.module_dist_paths = {}
        self.add_module("libtbx")

    def __enter__(self):
        # Save any existing module, then insert our fake one
        FakeLibTBX._previous_libtbx.append(sys.modules.get("libtbx", None))
        FakeLibTBX._previous_libtbx_load_env.append(
            sys.modules.get("libtbx.load_env", None)
        )
        sys.modules["libtbx"] = self._libtbx
        sys.modules["libtbx.load_env"] = self._libtbx.load_env
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Restore any previous module
        prev_libtbx = FakeLibTBX._previous_libtbx.pop()
        prev_load_env = FakeLibTBX._previous_libtbx_load_env.pop()
        if prev_load_env:
            sys.modules["libtbx.load_env"] = prev_load_env
        else:
            del sys.modules["libtbx.load_env"]
        if prev_libtbx:
            sys.modules["libtbx"] = prev_libtbx
        else:
            del sys.modules["libtbx"]

    def add_module(self, name):
        # type: (str) -> py.path.local
        """"Adds a libtbx module to the environment paths.

        Args:
            name: The module name. A path will be created.

        Returns:
            The dist path for the new module.
        """
        path = self._dist_path / name
        if not path.check():
            path.mkdir()
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
def libtbx(tmpdir):
    """Create a fake libtbx environment and return it"""
    with FakeLibTBX(tmpdir) as libtbx:
        yield libtbx
