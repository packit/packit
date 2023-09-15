# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re

import pytest
from flexmock import flexmock

from packit.config import CommonPackageConfig, Config, PackageConfig
from packit.constants import EXISTING_BODHI_UPDATE_REGEX
from packit.distgit import DistGit
from packit.local_project import LocalProjectBuilder


@pytest.mark.parametrize(
    "title, target_branch, source_branch, prs, exists",
    [
        (
            "Update",
            "f31",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                )
            ],
            True,
        ),
        (
            "Update",
            "f32",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                )
            ],
            False,
        ),
        (
            "Update",
            "f31",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit-stg",
                    source_branch="f31-update",
                )
            ],
            False,
        ),
        (
            "Update",
            "f31",
            "f32-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                )
            ],
            False,
        ),
    ],
)
def test_existing_pr(title, target_branch, source_branch, prs, exists):
    user_mock = flexmock().should_receive("get_username").and_return("packit").mock()
    local_project = LocalProjectBuilder().build(
        git_project=flexmock(service="something", get_pr_list=lambda: prs),
        git_service=flexmock(user=user_mock),
    )
    distgit = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(packages={"package": CommonPackageConfig()})
        ),
        local_project=local_project,
    )
    pr = distgit.existing_pr(title, target_branch, source_branch)
    if exists:
        assert pr is not None
    else:
        assert pr is None


# Test covers the regression from monorepo refactoring that affects sync-release
# on downstream, since it directly accessed the attribute on the dist-git config
# instead of accessing specific package, which can cause ambiguity…
def test_monorepo_regression():
    config = flexmock(fas_user="mf")

    # Construct the package config; DON'T MOCK TO ENSURE IT CAN BE REPRODUCED
    package_a = flexmock(allowed_gpg_keys=["0xDEADBEEF"])
    package_b = flexmock(allowed_gpg_keys=["0xDEADBEEF"])
    package_config = PackageConfig(
        {
            "a": package_a,
            "b": package_b,
        }
    )

    dg = DistGit(config, package_config)

    # Assume the config has been synced to dist-git, therefore is 1:1 to the
    # one passed to DistGit class
    dg._downstream_config = package_config

    assert dg.get_allowed_gpg_keys_from_downstream_config() == ["0xDEADBEEF"]


# Test covers regex used for silencing of Bodhi exceptions for existing updates
@pytest.mark.parametrize(
    "exception_message, matches",
    [
        (
            (
                '{"status": "error", "errors": ['
                '{"location": "body", "name": "builds", "description": '
                '"Cannot find any tags associated with build: packit-0.79.1-1.el9"},'
                '{"location": "body", "name": "builds", "description": "Cannot '
                'find release associated with build: packit-0.79.1-1.el9, tags: []"}]}'
            ),
            False,
        ),
        (
            (
                '{"status": "error", "errors": ['
                '{"location": "body", "name": "builds", '
                '"description": "Update for linux-system-roles-1.53.4-1.fc39 already exists"}]}'
            ),
            True,
        ),
    ],
)
def test_bodhi_regex(exception_message, matches):
    assert bool(re.match(EXISTING_BODHI_UPDATE_REGEX, exception_message)) == matches
