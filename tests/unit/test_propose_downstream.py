# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.cli.propose_downstream import get_dg_branches
from packit.config import (
    CommonPackageConfig,
    JobConfig,
    JobConfigTriggerType,
    JobType,
    PackageConfig,
)


@pytest.mark.parametrize(
    "package_config,cmdline,expected",
    [
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            None,
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=["file"],
                            ),
                        },
                    ),
                ],
            ),
            None,
            {
                "file",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            "cmdline",
            {
                "cmdline",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=["file"],
                            ),
                        },
                    ),
                ],
            ),
            "cmdline",
            {
                "cmdline",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=["file1", "file2"],
                            ),
                        },
                    ),
                ],
            ),
            None,
            {
                "file1",
                "file2",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            "cmdline1,cmdline2",
            {
                "cmdline1",
                "cmdline2",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            "rawhide",
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=["rawhide"],
                            ),
                        },
                    ),
                ],
            ),
            None,
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=["file1", "rawhide"],
                            ),
                        },
                    ),
                ],
            ),
            None,
            {
                "file1",
                "default_br",
            },
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            "cmdline1,rawhide",
            {
                "cmdline1",
                "default_br",
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_get_aliases")
def test_get_dist_git_branches(package_config, cmdline, expected):
    api = flexmock(PackitAPI)
    api.package_config = package_config
    git_project = flexmock(default_branch="default_br")
    local_project = flexmock(git_project=git_project)
    api.dg = flexmock(local_project=local_project)

    assert get_dg_branches(api, cmdline) == expected
