from flexmock import flexmock

from packit.cloned_project import ClonedProject


def test_cloned_project_name():
    project = ClonedProject(full_name="namespace/repository_name")
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_cloned_project_repo_namespace():
    project = ClonedProject(repo_name="repository_name", namespace="namespace")
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_cloned_project_project_flex():
    """Get git_url, namespace/repo and service from git_project"""
    project_mock = flexmock(
        repo="repository_name",
        namespace="namespace",
        service=flexmock(),
        get_git_urls=lambda: {"git": "ssh url"},
    )

    project = ClonedProject(
        git_project=project_mock,
        working_dir=flexmock(),
        git_repo=flexmock(active_branch="branch"),
    )
    assert project.git_service
    assert project.git_project
    assert project.repo_name == "repository_name"
    assert project.namespace == "namespace"
    assert project.full_name == "namespace/repository_name"


def test_cloned_project_git_repo_flex():
    """Get working_dir from git_repo"""
    project = ClonedProject(
        git_repo=flexmock(active_branch="branch", working_dir="something"),
        git_url=flexmock(),
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._branch == "branch"


def test_cloned_project_git_repo_url():
    """Get git_url from git_repo"""
    project = ClonedProject(
        git_repo=flexmock(active_branch="branch", working_dir="something")
        .should_receive("remote")
        .replace_with(lambda: flexmock(urls=["git/url"]))
        .once()
        .mock()
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._branch == "branch"
    assert project.git_url == "git/url"


def test_clone_project_checkout_branch_flex():
    """Checkout existing branch"""
    project = ClonedProject(
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
        branch="other",
        git_url=flexmock(),
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._branch == "other"


def test_clone_project_checkout_new_branch_flex():
    """Checkout newly created branch"""
    branches = {}
    project = ClonedProject(
        git_repo=flexmock(
            active_branch="branch", working_dir="something", branches=branches
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
        branch="other",
        git_url=flexmock(),
    )
    assert project.git_repo
    assert project.working_dir == "something"
    assert project._branch == "other"


def test_clone_project_get_project():
    """Get git_project from git_service and namespace/repo"""
    project = ClonedProject(
        repo_name="repo",
        namespace="namespace",
        git_service=flexmock()
        .should_receive("get_project")
        .with_args(repo="repo", namespace="namespace")
        .replace_with(lambda repo, namespace: flexmock())
        .mock(),
        git_url=flexmock(),
        working_dir=flexmock(),
        git_repo=flexmock(active_branch=flexmock()),
    )
    assert project.repo_name
    assert project.namespace
    assert project.git_service
    assert project.git_project
