# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.local_project import LocalProject


@pytest.mark.parametrize(
    "title, branch, prs, exists",
    [
        ("Update", "f31", [flexmock(title="Update", target_branch="f31")], True),
        ("Update", "f32", [flexmock(title="Update", target_branch="f31")], False),
        (
            "Something else",
            "f31",
            [flexmock(title="Update", target_branch="f31")],
            False,
        ),
        (
            "Something else",
            "f32",
            [flexmock(title="Update", target_branch="f31")],
            False,
        ),
    ],
)
def test_pr_exists(title, branch, prs, exists):
    local_project = LocalProject(
        git_project=flexmock(service="something", get_pr_list=lambda: prs),
        refresh=False,
    )
    distgit = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig()),
        local_project=local_project,
    )
    assert distgit.pr_exists(title, branch) == exists
