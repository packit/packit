from pathlib import Path

import pytest
from flexmock import flexmock

from packit.cli import utils
from packit.cli.utils import get_packit_api
from packit.local_project import LocalProject
from tests.spellbook import get_test_config, initiate_git_repo


def test_is_upstream(upstream_and_remote):
    upstream, _ = upstream_and_remote
    c = get_test_config()
    api = get_packit_api(
        config=c, local_project=LocalProject(working_dir=str(upstream))
    )
    assert api.upstream_local_project
    assert not api.downstream_local_project
    assert api.upstream_local_project.working_dir == str(upstream)


def test_is_downstream(distgit_and_remote):
    downstream, _ = distgit_and_remote
    c = get_test_config()
    api = get_packit_api(
        config=c, local_project=LocalProject(working_dir=str(downstream))
    )
    assert api.downstream_local_project
    assert not api.upstream_local_project
    assert api.downstream_local_project.working_dir == str(downstream)


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
        local_project=LocalProject(git_url="https://github.com/packit-service/ogr"),
    )
    assert api.upstream_local_project
    assert not api.downstream_local_project


@pytest.mark.parametrize(
    "remotes,package_config,is_upstream",
    [
        ([], flexmock(upstream_project_url=None, dist_git_base_url=None), True),
        ([], flexmock(upstream_project_url="some-url", dist_git_base_url=None), True),
        (
            [("origin", "https://github.com/packit-service/ogr.git")],
            flexmock(upstream_project_url="some-url", dist_git_base_url=None),
            True,
        ),
        (
            [("origin", "https://github.com/packit-service/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url=None,
            ),
            True,
        ),
        (
            [("upstream", "https://github.com/packit-service/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url=None,
            ),
            True,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url="src.fedoraproject.org",
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url=None,
                dist_git_base_url="https://src.fedoraproject.org",
            ),
            False,
        ),
        (
            [("origin", "https://src.fedoraproject.org/fork/user/rpms/python-ogr.git")],
            flexmock(
                upstream_project_url=None,
                dist_git_base_url="https://src.fedoraproject.org",
            ),
            False,
        ),
        (
            [("origin", "git@github.com:user/ogr.git")],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
            ),
            True,
        ),
        (
            [
                ("remote", "https://some.remote/ur/l.git"),
                ("origin", "git@github.com:user/ogr.git"),
            ],
            flexmock(
                upstream_project_url="https://github.com/packit-service/ogr",
                dist_git_base_url="https://src.fedoraproject.org",
            ),
            True,
        ),
    ],
)
def test_get_api(tmpdir, remotes, package_config, is_upstream):
    t = Path(str(tmpdir))

    repo = t / "project_repo"
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
        assert api.downstream_local_project
