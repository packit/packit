# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
E2E tests which utilize cockpit projects
"""

import pytest

from packit.cli.utils import get_packit_api
from packit.local_project import LocalProject
from packit.utils.commands import cwd
from tests.spellbook import (
    initiate_git_repo,
    get_test_config,
    # UP_SNAPD,
    UP_OSBUILD,
    UP_EDD,
    DG_OGR,
    build_srpm,
    UP_VSFTPD,
)


@pytest.fixture(
    params=[
        # disabling snapd for now, since it causes issues with the removal of
        # deprecated options and doesn't seem to be used anymore, will have
        # a look in a separate PR with resolution to either remove or try to fix
        # (UP_SNAPD, "2.41", "https://github.com/snapcore/snapd"),
        (UP_OSBUILD, "2", "https://github.com/osbuild/osbuild"),
        (UP_EDD, "0.3", "https://github.com/psss/edd"),
        (UP_VSFTPD, "3.0.3", "https://github.com/olysonek/vsftpd"),
        (DG_OGR, None, "https://src.fedoraproject.org/rpms/python-ogr"),
    ],
    ids=["osbuild", "edd", "vsftpd", "ogr"],
)
def example_repo(request, tmp_path):
    example_path, tag, remote = request.param
    u = tmp_path / "up"
    initiate_git_repo(u, tag=tag, copy_from=example_path, upstream_remote=remote)
    return u


def test_srpm_on_example(example_repo):
    c = get_test_config()
    api = get_packit_api(config=c, local_project=LocalProject(working_dir=example_repo))
    with cwd(example_repo):
        path = api.create_srpm()
    assert path.exists()
    build_srpm(path)
