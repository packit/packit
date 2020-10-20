# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.local_project import LocalProject


@pytest.mark.parametrize(
    "title, description, branch, prs, exists",
    [
        (
            "Update",
            "Upstream tag: 0.4.0\nUpstream commit: 6957453b",
            "f31",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                )
            ],
            True,
        ),
        (
            "Update",
            "Upstream tag: 0.4.0\nUpstream commit: 6957453b",
            "f31",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 8957453b",
                )
            ],
            False,
        ),
        (
            "Update",
            "Upstream tag: 0.4.0\nUpstream commit: 6957453b",
            "f32",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                )
            ],
            False,
        ),
    ],
)
def test_pr_exists(title, description, branch, prs, exists):
    local_project = LocalProject(
        git_project=flexmock(service="something", get_pr_list=lambda: prs),
        refresh=False,
    )
    distgit = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig()),
        local_project=local_project,
    )
    assert distgit.pr_exists(title, description, branch) == exists
