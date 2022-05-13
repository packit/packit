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
                    author="packit",
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
                    author="packit",
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
                    author="packit",
                )
            ],
            False,
        ),
        (
            "Update",
            "Upstream tag: 0.4.0\nUpstream commit: 6957453b",
            "f31",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit-stg",
                )
            ],
            False,
        ),
    ],
)
def test_existing_pr(title, description, branch, prs, exists):
    user_mock = flexmock().should_receive("get_username").and_return("packit").mock()
    local_project = LocalProject(
        git_project=flexmock(service="something", get_pr_list=lambda: prs),
        refresh=False,
        git_service=flexmock(user=user_mock),
    )
    distgit = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig()),
        local_project=local_project,
    )
    pr = distgit.existing_pr(title, description, branch)
    if exists:
        assert pr is not None
    else:
        assert pr is None
