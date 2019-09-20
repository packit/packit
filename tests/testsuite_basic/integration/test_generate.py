import unittest
from os import chdir

from tests.testsuite_basic.spellbook import call_packit


# TODO: fix the test
@unittest.skip("test fails in zuul, we have to investigate WHY")
def test_generate_pass(upstream_without_config):
    u = upstream_without_config
    chdir(u)

    assert not (u / ".packit.yaml").is_file()

    # This test requires packit on pythonpath
    result = call_packit(parameters=["generate"])

    assert result.exit_code == 0

    assert (u / ".packit.yaml").is_file()


def test_generate_fail(cwd_upstream_or_distgit):
    # This test requires packit on pythonpath
    result = call_packit(parameters=["generate"])

    assert result.exit_code == 2  # packit config already exists --force needed
