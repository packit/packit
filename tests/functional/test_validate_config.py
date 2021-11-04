# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functional tests the validate-config command
"""

from packit.utils.commands import cwd
from tests.functional.spellbook import call_real_packit


def test_srpm_command_for_path(upstream_or_distgit_path, tmp_path):
    with cwd(tmp_path):
        call_real_packit(
            parameters=["--debug", "validate-config", str(upstream_or_distgit_path)]
        )
