import sys
from pytest_libtbx.fake_libtbx import FakeTBXEnvironment


def test_basic_import():
    with FakeTBXEnvironment() as f:
        import libtbx

        assert libtbx.__dict__.get("__fake__") is True
    assert "libtbx" not in sys.modules


def test_discover():
    with FakeTBXEnvironment():
        from libtbx.test_utils.pytest import discover

        assert not discover()
