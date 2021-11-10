# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import tempfile
from pathlib import Path

import git
from flexmock import flexmock

from packit import local_project
from packit.local_project import LocalProject
from packit.utils import repo
from packit.utils.repo import RepositoryCache


def test_parse_repo_name_and_namespace_from_namespace():
    project = LocalProject(full_name="namespace/repository_name", refresh=False)
    changed = project._parse_repo_name_full_name_and_namespace()

    assert changed
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_parse_full_name_from_repo_and_namespace():
    project = LocalProject(
        repo_name="repository_name", namespace="namespace", refresh=False
    )
    changed = project._parse_repo_name_full_name_and_namespace()

    assert changed
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_parse_git_repo_from_working_dir():
    path = Path("some/example/path")
    flexmock(local_project).should_receive("is_git_repo").with_args(path).and_return(
        True
    )
    flexmock(
        git, Repo=flexmock(active_branch="branch", head=flexmock(is_detached=False))
    )
    project = LocalProject(working_dir=path, refresh=False)
    changed = project._parse_git_repo_from_working_dir()

    assert changed
    assert project.git_repo
    assert project.git_repo.active_branch == "branch"
    assert not project.working_dir_temporary


def test_parse_git_project_from_repo_namespace_and_git_service():
    service_mock = (
        flexmock()
        .should_receive("get_project")
        .with_args(repo="repo", namespace="namespace")
        .replace_with(lambda repo, namespace: flexmock())
        .mock()
    )

    project = LocalProject(
        git_service=service_mock, repo_name="repo", namespace="namespace", refresh=False
    )
    changed = project._parse_git_project_from_repo_namespace_and_git_service()

    assert changed
    assert project.git_service
    assert project.git_project


def test_parse_git_service_from_git_project():
    """Get git_url, namespace/repo and service from git_project"""
    project_mock = flexmock(service=flexmock())

    project = LocalProject(git_project=project_mock, refresh=False)
    changed = project._parse_git_service_from_git_project()

    assert changed
    assert project.git_service
    assert project.git_project


def test_parse_ref_from_git_repo():
    """Get ref from git_repo"""
    project = LocalProject(
        git_repo=flexmock(
            active_branch=flexmock(name="branch"), head=flexmock(is_detached=False)
        ),
        refresh=False,
    )
    changed = project._parse_ref_from_git_repo()

    assert changed
    assert project.git_repo
    assert project._ref == "branch"


def test_parse_ref_from_git_repo_detached():
    project = LocalProject(
        git_repo=flexmock(
            active_branch="branch",
            head=flexmock(is_detached=True, commit=flexmock(hexsha="sha")),
        ),
        refresh=False,
    )
    changed = project._parse_ref_from_git_repo()

    assert changed
    assert project.git_repo
    assert project._ref == "sha"


def test_parse_working_dir_from_git_repo():
    # TODO
    pass


def test_parse_git_repo_from_git_url():
    flexmock(local_project).should_receive("get_repo").with_args(
        url="http://some.example/url/reponame", directory=None
    ).and_return(flexmock())
    project = LocalProject(git_url="http://some.example/url/reponame", refresh=False)
    changed = project._parse_git_repo_from_git_url()

    assert changed
    assert project.git_url
    assert project.git_repo
    assert project.working_dir_temporary

    project.working_dir_temporary = False


def test_parse_git_url_from_git_project():
    project = LocalProject(
        git_project=flexmock()
        .should_receive("get_git_urls")
        .and_return({"git": "http://some.example/namespace/reponame"})
        .once()
        .mock(),
        refresh=False,
    )

    changed = project._parse_git_url_from_git_project()

    assert changed
    assert project.git_project
    assert project.git_url == "http://some.example/namespace/reponame"


def test_parse_repo_name_from_git_project():
    # TODO
    pass


def test_parse_namespace_from_git_project():
    project = LocalProject(git_project=flexmock(namespace="namespace"), refresh=False)

    changed = project._parse_namespace_from_git_project()

    assert changed
    assert project.git_project
    assert project.namespace
    assert project.namespace == "namespace"


def test_parse_git_url_from_git_repo():
    project = LocalProject(
        git_repo=flexmock(
            remotes=[flexmock(name="origin", url="git@github.com:org/name")]
        ),
        refresh=False,
    )

    changed = project._parse_git_url_from_git_repo()

    assert changed
    assert project.git_repo
    assert project.git_url == "git@github.com:org/name"


def test_parse_namespace_from_git_url():
    project = LocalProject(
        git_url="https://github.com/namespace/reponame", refresh=False
    )
    changed = project._parse_namespace_from_git_url()

    assert changed
    assert project.namespace
    assert project.namespace == "namespace"
    assert project.repo_name == "reponame"
    assert project.git_url == "https://github.com/namespace/reponame"


# CHECKOUT BRANCH


def test_clone_project_checkout_branch():
    """Checkout existing branch"""
    project = LocalProject(
        git_repo=flexmock(
            working_dir=Path("something"),
            git=flexmock().should_receive("checkout").with_args("other").once().mock(),
            commit=lambda: "9e131ba261d8d07fd1c55d8aff6ade085f5cd354",
        ),
        ref="other",
        git_url="git@github.com:org/name",
    )
    assert project.git_repo
    assert project.working_dir == Path("something")
    assert project._ref == "other"


# USAGE FROM CODE


def test_working_dir_namespace_repo_name():
    url = "https://server.git/my_namespace/package_name"
    work_dir = Path("./local/directory/to/git")
    flexmock(local_project).should_receive("is_git_repo").with_args(
        work_dir
    ).and_return(True)

    flexmock(git).should_receive("Repo").with_args(path=work_dir).and_return(
        flexmock(
            active_branch=flexmock(name="branch"), head=flexmock(is_detached=False)
        )
    )

    project = LocalProject(
        working_dir=work_dir,
        namespace="my_namespace",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock(get_git_urls=lambda: {"git": url}))
        .mock(),
    )

    assert project
    assert project.git_url == url
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"


def test_from_path_repo_name_git_service():
    flexmock(git.Repo).should_receive("clone_from").and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )

    flexmock(tempfile).should_receive("mkdtemp").and_return("some/temp/dir")

    project = LocalProject(
        git_url="https://server.git/my_namespace/package_name",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock())
        .mock(),
    )

    assert project
    assert project.working_dir == Path("some/temp/dir")
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"


def test_working_dir():
    work_dir = Path("./local/directory/to/git")
    flexmock(local_project).should_receive("is_git_repo").with_args(
        work_dir
    ).and_return(True)

    flexmock(git).should_receive("Repo").with_args(path=work_dir).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            head=flexmock(is_detached=False),
            remotes=[
                flexmock(
                    name="origin", url="https://server.git/my_namespace/package_name"
                )
            ],
        )
    )

    project = LocalProject(working_dir=work_dir)

    assert project
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.working_dir == work_dir
    assert project.git_repo
    assert project.ref == "branch"


# OFFLINE


def test_offline_git_project():
    """No get_project on offline"""

    project = LocalProject(
        repo_name="repo_name",
        namespace="namespace",
        git_service=flexmock().should_receive("get_project").times(0).mock(),
        offline=True,
    )
    assert project.repo_name == "repo_name"
    assert project.namespace == "namespace"
    assert project.git_service
    assert not project.git_project


def test_offline_git_service():
    """No git service on on offline"""

    project = LocalProject(
        repo_name="repo_name",
        namespace="namespace",
        git_project=flexmock(service="something")
        .should_receive("get_git_urls")
        .times(0)
        .mock(),
        offline=True,
    )
    assert project.repo_name == "repo_name"
    assert project.namespace == "namespace"
    assert project.git_project
    assert not project.git_service
    assert not project.git_url


def test_offline_no_clone():
    """No clone on offline"""
    flexmock(repo).should_receive("get_repo").times(0)
    flexmock(tempfile).should_receive("mkdtemp").times(0)
    flexmock(git.Repo).should_receive("clone_from").times(0)

    project = LocalProject(
        working_dir="some/example/path",
        git_url="http://some.example/url/reponame",
        offline=True,
    )
    assert project.working_dir == Path("some/example/path")
    assert project.git_url == "http://some.example/url/reponame"
    assert not project.git_repo


def test_offline_no_clone_no_temp_dir():
    """No clone on offline, no temp dir"""
    flexmock(repo).should_receive("get_repo").times(0)
    flexmock(tempfile).should_receive("mkdtemp").times(0)
    flexmock(git.Repo).should_receive("clone_from").times(0)
    project = LocalProject(git_url="http://some.example/url/reponame", offline=True)

    assert project.git_url == "http://some.example/url/reponame"
    assert not project.git_repo
    assert not project.working_dir


def test_clone_using_empty_cache():
    cache_path_mock = flexmock(
        is_dir=lambda: True,
        iterdir=lambda: [],
        joinpath=lambda x: "/reference/repo/package_name",
    )
    repo_cache = RepositoryCache(cache_path=cache_path_mock, add_new=False)

    flexmock(git.Repo).should_receive("clone_from").with_args(
        url="https://server.git/my_namespace/package_name",
        to_path="some/temp/dir",
        tags=True,
    ).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )

    flexmock(tempfile).should_receive("mkdtemp").and_return("some/temp/dir")

    project = LocalProject(
        git_url="https://server.git/my_namespace/package_name",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock())
        .mock(),
        cache=repo_cache,
    )

    assert project
    assert project.working_dir == Path("some/temp/dir")
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"


def test_clone_using_cache_present():
    reference_repo = flexmock(
        is_dir=lambda: True, __str__="/reference/repo/package_name", name="package_name"
    )
    cache_path_mock = flexmock(
        is_dir=lambda: True,
        iterdir=lambda: [reference_repo],
        joinpath=lambda x: "/reference/repo/package_name",
    )
    repo_cache = RepositoryCache(cache_path=cache_path_mock, add_new=False)

    flexmock(git.Repo).should_receive("clone_from").with_args(
        url="https://server.git/my_namespace/package_name",
        reference="/reference/repo/package_name",
        to_path="some/temp/dir",
        tags=True,
    ).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )

    flexmock(tempfile).should_receive("mkdtemp").and_return("some/temp/dir")

    project = LocalProject(
        git_url="https://server.git/my_namespace/package_name",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock())
        .mock(),
        cache=repo_cache,
    )

    assert project
    assert project.working_dir == Path("some/temp/dir")
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"


def test_clone_using_cache_not_present():
    reference_repo = flexmock(
        is_dir=lambda: True,
        __str__="/reference/repo/different_package",
        name="different_package",
    )
    cache_path_mock = flexmock(
        is_dir=lambda: True,
        iterdir=lambda: [reference_repo],
        joinpath=lambda x: "/reference/repo/package_name",
    )
    repo_cache = RepositoryCache(cache_path=cache_path_mock, add_new=False)

    flexmock(git.Repo).should_receive("clone_from").with_args(
        url="https://server.git/my_namespace/package_name",
        to_path="some/temp/dir",
        tags=True,
    ).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )

    flexmock(tempfile).should_receive("mkdtemp").and_return("some/temp/dir")

    project = LocalProject(
        git_url="https://server.git/my_namespace/package_name",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock())
        .mock(),
        cache=repo_cache,
    )

    assert project
    assert project.working_dir == Path("some/temp/dir")
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"


def test_clone_and_add_to_cache():
    cache_path_mock = flexmock(
        is_dir=lambda: True,
        iterdir=lambda: [],
        joinpath=lambda x: "/reference/repo/package_name",
    )
    repo_cache = RepositoryCache(cache_path=cache_path_mock, add_new=True)

    flexmock(git.Repo).should_receive("clone_from").with_args(
        url="https://server.git/my_namespace/package_name",
        to_path="/reference/repo/package_name",
        tags=True,
    ).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )
    flexmock(git.Repo).should_receive("clone_from").with_args(
        url="https://server.git/my_namespace/package_name",
        reference="/reference/repo/package_name",
        to_path="some/temp/dir",
        tags=True,
    ).and_return(
        flexmock(
            active_branch=flexmock(name="branch"),
            working_dir="some/temp/dir",
            head=flexmock(is_detached=False),
        )
    )

    flexmock(tempfile).should_receive("mkdtemp").and_return("some/temp/dir")

    project = LocalProject(
        git_url="https://server.git/my_namespace/package_name",
        repo_name="package_name",
        git_service=flexmock()
        .should_receive("get_project")
        .and_return(flexmock())
        .mock(),
        cache=repo_cache,
    )

    assert project
    assert project.working_dir == Path("some/temp/dir")
    assert project.git_url == "https://server.git/my_namespace/package_name"
    assert project.namespace == "my_namespace"
    assert project.repo_name == "package_name"
    assert project.git_service
    assert project.git_project
    assert project.git_repo
    assert project.ref == "branch"
