import tempfile
from os import path

import git
import requests
from flexmock import flexmock

from packit import local_project, utils
from packit.local_project import LocalProject


def test_local_project_full_name():
    project = LocalProject(full_name="namespace/repository_name")
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_local_project_repo_namespace():
    project = LocalProject(repo_name="repository_name", namespace="namespace")
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_local_project_working_dir_project():
    """Get git_url, namespace/repo and service from git_project"""
    project_mock = flexmock(
        repo="repository_name",
        namespace="namespace",
        service=flexmock(),
        get_git_urls=lambda: {"git": "git@github.com:namespace/repository_name"},
    )

    project = LocalProject(
        git_project=project_mock,
        working_dir=flexmock(),
        git_repo=flexmock(active_branch="branch", head=flexmock(is_detached=False))
        .should_receive("remote")
        .replace_with(
            lambda: flexmock(urls=["git@github.com:namespace/repository_name"])
        )
        .times(0)
        .mock(),
    )
    assert project.git_service
    assert project.git_project
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_local_project_repo_url():
    """Get working_dir from git_repo"""
    project = LocalProject(
        git_repo=flexmock(
            active_branch="branch",
            working_dir="something",
            head=flexmock(is_detached=False),
        ),
        git_url="http://some.example/url/reponame",
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._ref == "branch"


def test_local_project_repo():
    """Get git_url from git_repo"""
    project = LocalProject(
        git_repo=flexmock(
            active_branch="branch",
            working_dir="something",
            head=flexmock(is_detached=False),
        )
        .should_receive("remote")
        .replace_with(lambda: flexmock(urls=["git@github.com:org/name"]))
        .once()
        .mock()
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._ref == "branch"
    assert project.git_url == "git@github.com:org/name"


def test_clone_project_checkout_branch():
    """Checkout existing branch"""
    project = LocalProject(
        git_repo=flexmock(
            active_branch="branch",
            working_dir="something",
            branches={
                "other": flexmock(checkout=lambda: None)
                .should_receive("checkout")
                .once()
                .mock()
            },
        ),
        ref="other",
        git_url="git@github.com:org/name",
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._ref == "other"


def test_clone_project_checkout_new_branch():
    """Checkout newly created branch"""
    branches = {}
    project = LocalProject(
        git_repo=flexmock(
            active_branch="branch",
            working_dir="something",
            branches=branches,
            head=flexmock(is_detached=False),
        )
        .should_receive("create_head")
        .with_args("other")
        .replace_with(
            lambda x: branches.setdefault(
                x, flexmock().should_receive("checkout").once().mock()
            )
        )
        .once()
        .mock(),
        ref="other",
        git_url="git@github.com:org/name",
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._ref == "other"


def test_clone_project_service_repo_namespace():
    """Get git_project from git_service and namespace/repo"""
    project = LocalProject(
        repo_name="repo",
        namespace="namespace",
        git_service=flexmock()
        .should_receive("get_project")
        .with_args(repo="repo", namespace="namespace")
        .replace_with(lambda repo, namespace: flexmock())
        .mock(),
        git_url="git@github.com:org/name",
        working_dir=flexmock(),
        git_repo=flexmock(active_branch=flexmock(), head=flexmock(is_detached=False)),
    )
    assert project.repo_name
    assert project.namespace
    assert project.git_service
    assert project.git_project


def test_local_project_clone():
    flexmock(local_project).should_receive("get_repo").with_args(
        "http://some.example/url/reponame"
    ).and_return(
        flexmock(
            working_dir="some/example/path",
            active_branch="branch",
            head=flexmock(is_detached=False),
        )
    )

    project = LocalProject(git_url="http://some.example/url/reponame")

    assert project.git_url
    assert project.git_repo
    assert project.ref == "branch"
    assert project.working_dir_temporary

    project.working_dir_temporary = False


def test_local_project_repo_from_working_dir():
    flexmock(local_project).should_receive("is_git_repo").with_args(
        "https://some/example/path"
    ).and_return(True)
    flexmock(
        git,
        Repo=flexmock(
            active_branch="branch",
            remote=lambda: flexmock(urls=["git@github.com:org/name"]),
            head=flexmock(is_detached=False),
        ),
    )
    project = LocalProject(working_dir="https://some/example/path")

    assert project.git_url == "git@github.com:org/name"
    assert project.git_repo
    assert project.git_repo.active_branch == "branch"
    assert project.ref == "branch"
    assert not project.working_dir_temporary


def test_local_project_dir_url():
    flexmock(local_project).should_receive("get_repo").with_args(
        "http://some.example/url/reponame", "some/example/path"
    ).and_return(
        flexmock(
            working_dir="some/example/path",
            active_branch="branch",
            head=flexmock(is_detached=False),
        )
    )

    project = LocalProject(
        git_url="http://some.example/url/reponame", working_dir="some/example/path"
    )

    assert project.git_url == "http://some.example/url/reponame"
    assert project.git_repo
    assert project.ref == "branch"
    assert project.git_repo.active_branch == "branch"
    assert project.git_repo.working_dir == "some/example/path"
    assert not project.working_dir_temporary


def test_local_project_offline_git_project():
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


def test_local_project_offline_git_service():
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


def test_local_project_offline_no_clone():
    """No clone on offline"""
    flexmock(utils).should_receive("get_repo").times(0)
    flexmock(tempfile).should_receive("mkdtemp").times(0)
    flexmock(git.Repo).should_receive("clone_from").times(0)

    project = LocalProject(
        working_dir="some/example/path",
        git_url="http://some.example/url/reponame",
        offline=True,
    )
    assert project.working_dir == "some/example/path"
    assert project.git_url == "http://some.example/url/reponame"
    assert not project.git_repo


def test_local_project_offline_no_clone_no_temp_dir():
    """No clone on offline, no temp dir"""
    flexmock(utils).should_receive("get_repo").times(0)
    flexmock(tempfile).should_receive("mkdtemp").times(0)
    flexmock(git.Repo).should_receive("clone_from").times(0)
    project = LocalProject(git_url="http://some.example/url/reponame", offline=True)

    assert project.git_url == "http://some.example/url/reponame"
    assert not project.git_repo
    assert not project.working_dir


def test_local_project_path_or_url_path():
    """isdir=True"""
    flexmock(path).should_receive("isdir").and_return(True).once()
    project = LocalProject(
        path_or_url="https://some/example/path",
        git_repo=flexmock(branches={"other": flexmock(checkout=lambda: None)}),
        git_url="https://nothing/else/matters",
        ref="other",
    )

    assert project.working_dir == "https://some/example/path"
    assert project.git_repo
    assert project.git_url == "https://nothing/else/matters"


def test_local_project_path_or_url_overwrite():
    """overwrite the path_or_url with working_dir"""
    flexmock(path).should_receive("isdir").and_return(True).once()
    project = LocalProject(
        path_or_url="https://some/example/path",
        working_dir="new/dir",
        git_repo=flexmock(branches={"other": flexmock(checkout=lambda: None)}),
        git_url="https://nothing/else/matters",
        ref="other",
    )

    assert project.working_dir == "new/dir"
    assert project.git_repo
    assert project.git_url == "https://nothing/else/matters"


def test_local_project_path_or_url_url():
    """isdir=False requests.head => ok=True"""
    flexmock(path).should_receive("isdir").and_return(False).once()
    flexmock(requests).should_receive("head").and_return(flexmock(ok=True)).once()

    project = LocalProject(
        path_or_url="http://some.example/url/reponame",
        git_repo=flexmock(branches={"other": flexmock(checkout=lambda: None)}),
        working_dir="nothing",
        ref="other",
    )

    assert project.git_url == "http://some.example/url/reponame"
    assert project.git_repo
    assert project.working_dir == "nothing"


def test_local_project_path_or_url_url_overwrite():
    """overwrite the path_or_url with git_url"""
    flexmock(path).should_receive("isdir").and_return(False).once()
    flexmock(requests).should_receive("head").and_return(flexmock(ok=True)).once()

    project = LocalProject(
        path_or_url="http://some.example/url/reponame",
        git_repo=flexmock(branches={"other": flexmock(checkout=lambda: None)}),
        working_dir="nothing",
        git_url="http://some.new/url/reponame",
        ref="other",
    )

    assert project.git_url == "http://some.new/url/reponame"
    assert project.git_repo
    assert project.working_dir == "nothing"


def test_local_project_path_or_url_nok():
    """isdir=False requests.head => ok=False"""
    flexmock(path).should_receive("isdir").and_return(False).once()
    flexmock(requests).should_receive("head").and_return(flexmock(ok=False)).once()

    project = LocalProject(path_or_url="http://some.example/url/reponame")

    assert not project.git_url
