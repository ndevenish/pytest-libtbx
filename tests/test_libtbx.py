# -*- coding: utf-8 -*-

import pytest

def test_run_tests_found(testdir):
    testdir.makepyfile(
        run_tests=""""""
    )
    # cfg = testdir.parseconfig()
    # path = testdir.tmpdir / "run_tests.py"
    # node = testdir.getnode(cfg, path)

    import pdb; pdb.set_trace()
    result = testdir.runpytest('--collect-only', '-v')
    import pdb
    pdb.set_trace()

@pytest.mark.skip
def test_empty_dials_runtest(testdir):
    testdir.makepyfile(
        run_tests="""
    from libtbx.test_utils.pytest import discover
    tst_list = discover()"""
    )
    result = testdir.runpytest('--collect-only')

# def test_bar_fixture(testdir):
#     """Make sure that pytest accepts our fixture."""

#     # create a temporary pytest test module
#     testdir.makepyfile("""
#         def test_sth(bar):
#             assert bar == "europython2015"
#     """)

#     # run pytest with the following cmd args
#     result = testdir.runpytest(
#         '--foo=europython2015',
#         '-v'
#     )

#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         '*::test_sth PASSED*',
#     ])

#     # make sure that that we get a '0' exit code for the testsuite
#     assert result.ret == 0


# def test_help_message(testdir):
#     result = testdir.runpytest(
#         '--help',
#     )
#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         'libtbx:',
#         '*--foo=DEST_FOO*Set the value for the fixture "bar".',
#     ])


# def test_hello_ini_setting(testdir):
#     testdir.makeini("""
#         [pytest]
#         HELLO = world
#     """)

#     testdir.makepyfile("""
#         import pytest

#         @pytest.fixture
#         def hello(request):
#             return request.config.getini('HELLO')

#         def test_hello_world(hello):
#             assert hello == 'world'
#     """)

#     result = testdir.runpytest('-v')

#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         '*::test_hello_world PASSED*',
#     ])

#     # make sure that that we get a '0' exit code for the testsuite
#     assert result.ret == 0
