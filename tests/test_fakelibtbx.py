
from pytest_libtbx.fake_libtbx import FakeTBXEnvironment

def test_basic_import():
  with FakeTBXEnvironment() as f:
    import libtbx
    import pdb
    pdb.set_trace()