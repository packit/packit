# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functional tests for local-build command
"""
from pathlib import Path
from subprocess import CalledProcessError

import pytest
from distro import linux_distribution

from tests.functional.spellbook import call_real_packit


def test_rpm_command(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "build", "locally"], cwd=ogr_distgit_and_remote[0]
    )
    rpm_paths = ogr_distgit_and_remote[0].glob("noarch/*.rpm")

    assert all(rpm_path.exists() for rpm_path in rpm_paths)


def test_local_build_with_remote_good(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "--remote", "origin", "build", "locally"],
        cwd=ogr_distgit_and_remote[0],
    )
    rpm_paths = ogr_distgit_and_remote[0].glob("noarch/*.rpm")

    assert all(rpm_path.exists() for rpm_path in rpm_paths)


def test_local_build_with_remote_bad(ogr_distgit_and_remote):
    with pytest.raises(CalledProcessError) as ex:
        call_real_packit(
            parameters=["--debug", "--remote", "burcak", "build", "locally"],
            cwd=ogr_distgit_and_remote[0],
            return_output=True,
        )
    assert b"Remote named 'burcak' didn't exist" in ex.value.output


@pytest.mark.skipif(
    linux_distribution()[0].startswith("CentOS"),
    reason="No rpmautospec-rpm-macros installed",
)
def test_rpm_command_for_path(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "build", "locally", str(ogr_distgit_and_remote[0])]
    )
    rpm_paths = Path.cwd().glob("noarch/*.rpm")
    assert all(rpm_path.exists() for rpm_path in rpm_paths)
