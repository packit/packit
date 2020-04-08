# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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

import logging
from enum import Enum

from packit.exceptions import PackitConfigException

logger = logging.getLogger(__name__)


class JobType(Enum):
    """ Type of the job to execute: pick the correct handler """

    propose_downstream = "propose_downstream"
    check_downstream = "check_downstream"
    build = "build"
    sync_from_downstream = "sync_from_downstream"
    copr_build = "copr_build"
    production_build = "production_build"  # koji build
    add_to_whitelist = "add_to_whitelist"
    tests = "tests"
    report_test_results = "report_test_results"
    pull_request_action = "pull_request_action"
    copr_build_finished = "copr_build_finished"
    copr_build_started = "copr_build_started"


class JobConfigTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"


class JobConfig:
    def __init__(self, type: JobType, trigger: JobConfigTriggerType, metadata: dict):
        self.type = type
        self.trigger: JobConfigTriggerType = trigger
        self.metadata: dict = metadata

    def __repr__(self):
        return (
            f"JobConfig(job={self.type}, trigger={self.trigger}, meta={self.metadata})"
        )

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "JobConfig":
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema, MM3

        if MM3:
            config = JobConfigSchema().load(raw_dict)
        else:  # v2
            config = JobConfigSchema(strict=True).load(raw_dict).data
        logger.debug(config)

        return config

    def __eq__(self, other: object):
        if not isinstance(other, JobConfig):
            raise PackitConfigException("Provided object is not a JobConfig instance.")
        return (
            self.type == other.type
            and self.trigger == other.trigger
            and self.metadata == other.metadata
        )


default_jobs = [
    JobConfig(
        type=JobType.tests,
        trigger=JobConfigTriggerType.pull_request,
        metadata={"targets": ["fedora-stable"]},
    ),
    JobConfig(
        type=JobType.propose_downstream,
        trigger=JobConfigTriggerType.release,
        metadata={"dist-git-branch": ["fedora-all"]},
    ),
]
