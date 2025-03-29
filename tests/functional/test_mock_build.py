
# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from tests.functional.spellbook import call_real_packit


def test_build_in_mock_default_resultdir(upstream_and_remote):
    cwd, _ = upstream_and_remote

    call_real_packit(
        parameters=["--debug", "build", "in-mock", "-r", "fedora-rawhide-x86_64"],
        cwd=cwd,
    )

    rpm_paths = list(cwd.glob("noarch/*.rpm"))

    assert rpm_paths, "No RPMs were found in the expected directory!"
    assert all(
        rpm_path.exists() for rpm_path in rpm_paths
    ), "Some RPM files do not exist!"
