# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.config import PackageConfig
from packit.cli.propose_downstream import get_dg_branches

from packit.config import (
    JobType,
    JobConfigTriggerType,
    JobConfig,
)
from packit.config.job_config import JobMetadataConfig


@pytest.mark.parametrize(
    "package_config,cmdline,expected",
    [
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                    )
                ],
            ),
            None,
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(dist_git_branches=["file"]),
                    )
                ],
            ),
            None,
            {
                "file",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                    )
                ],
            ),
            "cmdline",
            {
                "cmdline",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(dist_git_branches=["file"]),
                    )
                ],
            ),
            "cmdline",
            {
                "cmdline",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(
                            dist_git_branches=["file1", "file2"]
                        ),
                    )
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
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                    )
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
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                    )
                ],
            ),
            "rawhide",
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(dist_git_branches=["rawhide"]),
                    )
                ],
            ),
            None,
            {
                "default_br",
            },
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(
                            dist_git_branches=["file1", "rawhide"]
                        ),
                    )
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
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                    )
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
def test_get_dist_git_branches(package_config, cmdline, expected):

    api = flexmock(PackitAPI)
    api.package_config = package_config
    git_project = flexmock(default_branch="default_br")
    local_project = flexmock(git_project=git_project)
    api.dg = flexmock(local_project=local_project)

    assert get_dg_branches(api, cmdline) == expected
