=============
pytest-libtbx
=============
tatus on AppVeyor

pytest plugin to load libtbx-style tests.

Libtbx-style testing has a `run_tests.py` file in the module root that
explicitly lists all tests and the parameters to run them with in a
`tst_list` variable.

- Incompatible `test_*.py` files won't be collected by pytest
- Tests are run in-process by default, which should help with speed
- `tst_list_slow` is supported by converting to the dials/xia2-style
  `regression` marker - these will be skipped unless you pass `--regression`.

Modules that aren't pytest-compatible won't be otherwise collected. This
is determined by the presence of a call to `libtbx.test_utils.pytest.discover()`
inside the `run_tests.py` - this