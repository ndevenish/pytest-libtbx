=============
pytest-libtbx
=============

.. image:: https://img.shields.io/pypi/v/pytest-libtbx.svg
    :target: https://pypi.org/project/pytest-libtbx
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-libtbx.svg
    :target: https://pypi.org/project/pytest-libtbx
    :alt: Python versions

.. image:: https://travis-ci.org/ndevenish/pytest-libtbx.svg?branch=master
    :target: https://travis-ci.org/ndevenish/pytest-libtbx
    :alt: See Build Status on Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/ndevenish/pytest-libtbx?branch=master
    :target: https://ci.appveyor.com/project/ndevenish/pytest-libtbx/branch/master
    :alt: See Build Status on AppVeyor

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

----


Features
--------

* Reads `run_tests.py` 


Requirements
------------

* TODO


Installation
------------

You can install "pytest-libtbx" via `pip`_ from `PyPI`_::

    $ pip install pytest-libtbx


Usage
-----

* TODO

Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `BSD-3`_ license, "pytest-libtbx" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/ndevenish/pytest-libtbx/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
