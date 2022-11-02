# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.cli import utils
from packit.cli.utils import get_packit_api
from packit.config import CommonPackageConfig, JobConfig
from packit.config.job_config import JobType, JobConfigTriggerType
from packit.local_project import LocalProject
from tests.spellbook import get_test_config, initiate_git_repo


def test_is_upstream(upstream_and_remote):
    upstream, _ = upstream_and_remote
    c = get_test_config()
    api = get_packit_api(config=c, local_project=LocalProject(working_dir=upstream))
    assert api.upstream_local_project
    assert not api.downstream_local_project
    assert api.upstream_local_project.working_dir == upstream


def test_is_downstream(distgit_and_remote):
    downstream, _ = distgit_and_remote
    c = get_test_config()
    api = get_packit_api(config=c, local_project=LocalProject(working_dir=downstream))
    assert api.downstream_local_project
    assert not api.upstream_local_project
    assert api.downstream_local_project.working_dir == downstream


def test_url_is_downstream():
    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProject(git_url="https://src.fedoraproject.org/rpms/packit"),
    )
    assert api.downstream_local_project
    assert not api.upstream_local_project


def test_url_is_upstream():
    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProject(git_url="https://github.com/packit/ogr"),
    )
    assert api.upstream_local_project
    assert not api.downstream_local_project


@pytest.mark.parametrize(
    "remotes,package_config,is_upstream",
    [
        (
            [],
            flexmock(
                upstream_project_url=None, dist_git_base_url=None, synced_files=None
            ),
            True,
        ),
        (
            [],
            flexmock(
                upstream_project_url="some-url",
                dist_git_base_url=None,
                synced_files=None,
            ),
            True,
        ),
        (
            [("origin", "https://github.com/packit/ogr.git")],
            flexmock(
                upstream_project_url="some-url",
                dist_git_base_url=None,
                synced_files=None,
            ),
            True,
        ),
        (
            [("origin", "https://github.com/packit/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url=None,
                synced_files=None,
            ),
            True,
        ),
        (
            [("upstream", "https://github.com/packit/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url=None,
                synced_files=None,
            ),
            True,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
                synced_files=None,
                downstream_package_name=None,
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url="src.fedoraproject.org",
                synced_files=None,
                downstream_package_name=None,
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url=None,
                dist_git_base_url="https://src.fedoraproject.org",
                synced_files=None,
                downstream_package_name=None,
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/fork/user/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url=None,
                dist_git_base_url="https://src.fedoraproject.org",
                synced_files=None,
                downstream_package_name=None,
            ),
            False,
        ),
        (
            [("origin", "git@github.com:user/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
                synced_files=None,
            ),
            True,
        ),
        (
            [
                ("remote", "https://some.remote/ur/l.git"),
                ("origin", "git@github.com:user/ogr.git"),
            ],
            flexmock(
                upstream_project_url="https://github.com/packit/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
                synced_files=None,
            ),
            True,
        ),
        (
            [
                ("remote", "https://some.remote/ur/l.git"),
                ("origin", "git@github.com:user/ogr.git"),
            ],
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "package": CommonPackageConfig(
                        upstream_project_url="https://github.com/packit/ogr",
                    )
                },
            ),
            True,
        ),
    ],
)
def test_get_api(tmp_path, remotes, package_config, is_upstream):
    repo = tmp_path / "project_repo"
    repo.mkdir(parents=True, exist_ok=True)
    initiate_git_repo(repo, remotes=remotes)

    flexmock(utils).should_receive("get_local_package_config").and_return(
        package_config
    )

    c = get_test_config()
    api = get_packit_api(config=c, local_project=LocalProject(working_dir=str(repo)))

    if is_upstream:
        assert api.upstream_local_project
    else:
        flexmock(PackitAPI).should_receive("init_kerberos_ticket").once()
        assert api.downstream_local_project
        assert api.dg
