# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
E2E tests which utilize cockpit projects
"""

import pytest

from packit.cli.utils import get_packit_api
from packit.local_project import CALCULATE, LocalProjectBuilder
from packit.utils.commands import cwd
from tests.spellbook import (
    DG_OGR,
    UP_EDD,
    UP_VSFTPD,
    build_srpm,
    get_test_config,
    initiate_git_repo,
    is_suitable_pyforgejo_rpm_installed,
)


@pytest.fixture(
    params=[
        (UP_EDD, "0.3", "https://github.com/psss/edd"),
        (UP_VSFTPD, "3.0.3", "https://github.com/olysonek/vsftpd"),
        pytest.param(
            (DG_OGR, None, "https://src.fedoraproject.org/rpms/python-ogr"),
            marks=pytest.mark.xfail(
                not is_suitable_pyforgejo_rpm_installed(),
                reason="ogr (S)RPM build requires python3-pyforgejo >= 2.0.0",
            ),
        ),
    ],
    ids=["edd", "vsftpd", "ogr"],
)
def example_repo(request, tmp_path):
    example_path, tag, remote = request.param
    u = tmp_path / "up"
    initiate_git_repo(u, tag=tag, copy_from=example_path, upstream_remote=remote)
    return u


def test_srpm_on_example(example_repo):
    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProjectBuilder().build(
            working_dir=example_repo,
            git_repo=CALCULATE,
        ),
    )
    with cwd(example_repo):
        path = api.create_srpm()
    assert path.exists()
    build_srpm(path)
