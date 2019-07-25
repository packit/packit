from os import chdir
import unittest

from tests.spellbook import call_packit


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


def test_generate_fail(upstream_n_distgit):
    u, d = upstream_n_distgit
    chdir(u)

    # This test requires packit on pythonpath
    result = call_packit(parameters=["generate"])

    assert result.exit_code == 2  # packit config already exists --force needed
