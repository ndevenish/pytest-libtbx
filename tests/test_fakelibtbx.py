from pytest_libtbx.fake_env import CustomRuntestsEnvironment


def test_basic_import(libtbx):
    with CustomRuntestsEnvironment() as f:
        import libtbx

        assert libtbx.test_utils.pytest.discover == f.pytest_discover


def test_discover(libtbx):
    with CustomRuntestsEnvironment():
        from libtbx.test_utils.pytest import discover

        assert not discover()
