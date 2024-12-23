# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.cli.dist_git_init import DistGitInitializer


@pytest.mark.parametrize(
    "initializer,expected_config_dict",
    [
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
            ),
            {
                "upstream_project_url": "my-url",
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="only-url",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                upstream_tag_exclude="regex-1",
                upstream_tag_include="regex-2",
                upstream_tag_template="v{version}",
                issue_repository="issue-repo-url",
            ),
            {
                "upstream_project_url": "my-url",
                "upstream_tag_template": "v{version}",
                "upstream_tag_include": "regex-2",
                "upstream_tag_exclude": "regex-1",
                "issue_repository": "issue-repo-url",
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="basic-options",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                dist_git_branches="fedora-38,fedora-39",
            ),
            {
                "upstream_project_url": "my-url",
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-38", "fedora-39"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-38", "fedora-39"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-38", "fedora-39"],
                    },
                ],
            },
            id="dist-git-branches",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                allowed_committers="admin1,admin2",
            ),
            {
                "upstream_project_url": "my-url",
                "allowed_committers": ["admin1", "admin2"],
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="allowed-committers",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                allowed_pr_authors="admin1,admin2",
            ),
            {
                "upstream_project_url": "my-url",
                "allowed_pr_authors": ["admin1", "admin2"],
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="allowed_pr_authors",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                no_bodhi_update=True,
            ),
            {
                "upstream_project_url": "my-url",
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "koji_build",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="no-bodhi",
        ),
        pytest.param(
            DistGitInitializer(
                config=None,
                path_or_url=None,
                upstream_git_url="my-url",
                no_koji_build=True,
            ),
            {
                "upstream_project_url": "my-url",
                "jobs": [
                    {
                        "job": "pull_from_upstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                    {
                        "job": "bodhi_update",
                        "trigger": "commit",
                        "dist_git_branches": ["fedora-rawhide"],
                    },
                ],
            },
            id="no-koji",
        ),
    ],
)
def test_generate_pacakge_config_dict(
    initializer: DistGitInitializer,
    expected_config_dict: dict,
):
    assert initializer.generate_package_config_dict() == expected_config_dict


def test_parse_actions_from_file(tmp_path):
    actions_file = tmp_path / "actions.yaml"
    actions_file.write_text(
        """\
changelog-entry:
- bash -c 'some command'
""",
    )
    initializer = DistGitInitializer(
        config=None,
        path_or_url=None,
        upstream_git_url=None,
        actions_file=actions_file,
    )
    assert initializer.parse_actions_from_file() == {
        "changelog-entry": ["bash -c 'some command'"],
    }
