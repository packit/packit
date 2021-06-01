# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packit.utils.commands import cwd

from tests.spellbook import call_packit


def test_init_pass(upstream_without_config):
    with cwd(upstream_without_config):
        assert not (upstream_without_config / ".packit.yaml").is_file()

        # This test requires packit on pythonpath
        result = call_packit(parameters=["init"])

        assert result.exit_code == 0

        assert (upstream_without_config / ".packit.yaml").is_file()


def test_init_fail(cwd_upstream_or_distgit):
    result = call_packit(parameters=["init"], working_dir=str(cwd_upstream_or_distgit))

    assert result.exit_code == 2  # packit config already exists --force needed
