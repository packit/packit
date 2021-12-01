# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functional tests for prepare-sources command
"""
from pathlib import Path

from packit.utils.commands import cwd
from tests.functional.spellbook import call_real_packit


def test_prepare_sources_command_for_path(upstream_or_distgit_path, tmp_path):
    with cwd(tmp_path):
        call_real_packit(
            parameters=[
                "--debug",
                "prepare-sources",
                "--result-dir",
                Path.cwd(),
                str(upstream_or_distgit_path),
            ]
        )

        tarball_path = list(Path.cwd().glob("*.tar.gz"))[0]
        assert tarball_path.exists()
        specfile_path = list(Path.cwd().glob("*.spec"))[0]
        assert specfile_path.exists()


def test_prepare_sources_command(cwd_upstream_or_distgit):
    call_real_packit(
        parameters=["--debug", "prepare-sources"],
        cwd=cwd_upstream_or_distgit,
    )
    result_dir = cwd_upstream_or_distgit.joinpath("prepare_sources_result")
    assert result_dir.exists()

    tarball_path = list(result_dir.glob("*.tar.gz"))[0]
    assert tarball_path.exists()
    specfile_path = list(result_dir.glob("*.spec"))[0]
    assert specfile_path.exists()
