# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from bodhi.client.bindings import BodhiClient
from flexmock import flexmock

from packit.status import Status


def test_status_updates(config_mock, package_config_mock, upstream_mock, distgit_mock):
    flexmock(
        BodhiClient,
        query=lambda packages, page: {
            "updates": [
                {
                    "title": "python-requre-0.8.1-2.fc33",
                    "karma": 2,
                    "status": "stable",
                    "release": {"branch": "f33"},
                },
                {
                    "title": "python-requre-0.8.1-2.fc34",
                    "karma": 3,
                    "status": "stable",
                    "release": {"branch": "f34"},
                },
            ],
            "page": 1,
            "pages": 1,
        },
    )

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_updates()
    assert table == [
        ["python-requre-0.8.1-2.fc33", 2, "stable"],
        ["python-requre-0.8.1-2.fc34", 3, "stable"],
    ]


def test_get_downstream_prs_with_iterable(
    config_mock,
    package_config_mock,
    upstream_mock,
    distgit_mock,
):
    """Test that get_downstream_prs works when get_pr_list returns an Iterable
    (e.g. ForgejoProject) instead of a list (e.g. PagureProject)."""
    fake_prs = [
        flexmock(id=1, title="Fix bug", url="https://forgejo.example/pr/1"),
        flexmock(id=2, title="Add feature", url="https://forgejo.example/pr/2"),
    ]
    # Return a generator to simulate ForgejoProject.get_pr_list() returning Iterable
    flexmock(distgit_mock.local_project.git_project).should_receive(
        "get_pr_list",
    ).and_return(pr for pr in fake_prs)

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_downstream_prs()

    assert table == [
        (1, "Fix bug", "https://forgejo.example/pr/1"),
        (2, "Add feature", "https://forgejo.example/pr/2"),
    ]


def test_get_downstream_prs_truncation_with_iterable(
    config_mock,
    package_config_mock,
    upstream_mock,
    distgit_mock,
):
    """Test that get_downstream_prs truncates to number_of_prs when the
    iterable contains more PRs than the limit (default is 5)."""
    fake_prs = [
        flexmock(id=i, title=f"PR {i}", url=f"https://forgejo.example/pr/{i}")
        for i in range(1, 8)  # 7 PRs
    ]
    flexmock(distgit_mock.local_project.git_project).should_receive(
        "get_pr_list",
    ).and_return(pr for pr in fake_prs)

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_downstream_prs()  # default number_of_prs=5

    assert len(table) == 5
    assert table == [
        (1, "PR 1", "https://forgejo.example/pr/1"),
        (2, "PR 2", "https://forgejo.example/pr/2"),
        (3, "PR 3", "https://forgejo.example/pr/3"),
        (4, "PR 4", "https://forgejo.example/pr/4"),
        (5, "PR 5", "https://forgejo.example/pr/5"),
    ]


def test_get_downstream_prs_empty_iterable(
    config_mock,
    package_config_mock,
    upstream_mock,
    distgit_mock,
):
    """Test that get_downstream_prs returns an empty list when get_pr_list()
    returns an empty iterator (e.g. a repo with no open PRs)."""
    flexmock(distgit_mock.local_project.git_project).should_receive(
        "get_pr_list",
    ).and_return(iter([]))

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_downstream_prs()

    assert table == []


def test_get_downstream_prs_with_plain_list(
    config_mock,
    package_config_mock,
    upstream_mock,
    distgit_mock,
):
    """Test backward compatibility: get_downstream_prs works when get_pr_list
    returns a plain list (e.g. PagureProject), not just an Iterable."""
    fake_prs = [
        flexmock(id=1, title="Pagure fix", url="https://src.fedoraproject.org/pr/1"),
        flexmock(
            id=2,
            title="Pagure feature",
            url="https://src.fedoraproject.org/pr/2",
        ),
    ]
    flexmock(distgit_mock.local_project.git_project).should_receive(
        "get_pr_list",
    ).and_return(
        fake_prs,
    )  # plain list, not a generator

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_downstream_prs()

    assert table == [
        (1, "Pagure fix", "https://src.fedoraproject.org/pr/1"),
        (2, "Pagure feature", "https://src.fedoraproject.org/pr/2"),
    ]
