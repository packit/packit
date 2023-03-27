# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from copy import deepcopy
from enum import Enum
from logging import getLogger
from typing import List, Dict

from packit.config.aliases import DEFAULT_VERSION
from packit.config.common_package_config import CommonPackageConfig, MultiplePackages
from packit.exceptions import PackitConfigException

logger = getLogger(__name__)


class JobType(Enum):
    """Type of the job used by users in the config"""

    propose_downstream = "propose_downstream"
    pull_from_upstream = "pull_from_upstream"
    build = "build"  # deprecated
    sync_from_downstream = "sync_from_downstream"
    copr_build = "copr_build"
    production_build = "production_build"  # deprecated
    upstream_koji_build = "upstream_koji_build"
    koji_build = "koji_build"  # downstream koji build
    tests = "tests"
    bodhi_update = "bodhi_update"
    vm_image_build = "vm_image_build"


DEPRECATED_JOB_TYPES = {
    JobType.build: "The `build` job type aimed to be an alias for "
    "`copr_build` when Packit supported just one "
    "build type. "
    "There are currently more types of builds and just `build` can be misleading. "
    "Please, be explicit and use `copr_build` instead.",
    JobType.production_build: "The `production_build` name for upstream Koji build is misleading "
    "because it is not used to run production/non-scratch builds and "
    "because it can be confused with the `koji_build` job that is triggered for dist-git commits. "
    "(The `koji_build` job can trigger both scratch and non-scratch/production builds.) "
    "To be explicit, use `upstream_koji_build` for builds triggered in upstream "
    "and `koji_build` for builds triggered in downstream.",
}


class JobConfigTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"


class JobConfig(MultiplePackages):
    """
    Definition of a job.

    Attributes:
        type: Type of the job, that is: the action to be performed by Packit.
        trigger: Event triggering the job.
    """

    def __init__(
        self,
        type: JobType,
        trigger: JobConfigTriggerType,
        packages: Dict[str, CommonPackageConfig],
        skip_build: bool = False,
    ):
        super().__init__(packages)
        # Directly manipulating __dict__ is not recommended.
        # It is done here to avoid triggering __setattr__ and
        # should be removed once support for a single package is
        # dropped from config objects.
        self.__dict__["type"] = type
        self.__dict__["trigger"] = trigger
        self.__dict__["skip_build"] = skip_build

    def __repr__(self):
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema

        s = JobConfigSchema()
        # For __repr__() return a JSON-encoded string, by using dumps().
        # Mind the 's'!
        return f"JobConfig: {s.dumps(self)}"

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "JobConfig":
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema

        config = JobConfigSchema().load(raw_dict)
        logger.debug(f"Loaded config: {config}")

        return config

    def __eq__(self, other: object):
        if not isinstance(other, JobConfig):
            raise PackitConfigException("Provided object is not a JobConfig instance.")
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema

        s = JobConfigSchema()
        # Compare the serialized objects.
        return s.dump(self) == s.dump(other)


class JobConfigView(JobConfig):
    def __init__(self, job_config: JobConfig, package: str):
        self._view_for_package = package
        self._job_config_packages = job_config.packages
        job_config_view_packages = {package: job_config.packages[package]}
        super().__init__(
            job_config.type,
            job_config.trigger,
            job_config_view_packages,
            job_config.skip_build,
        )

    @property
    def package(self) -> str:
        """The name for the package related with this JobConfigView?"""
        return self._view_for_package

    def __eq__(self, other: object):
        if not isinstance(other, JobConfigView):
            if isinstance(other, JobConfig):
                return False
            raise PackitConfigException(
                "Provided object is not a JobConfigView instance."
            )
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema

        s = JobConfigSchema()
        # Compare the serialized objects.
        return s.dump(self) == s.dump(other)

    @property
    def identifier(self):
        """
        Decorate any identifier attribute with the
        reference to the package.
        """
        original_identifier = super().__getattr__("identifier")
        if original_identifier is None:
            return self._view_for_package
        return original_identifier


def get_default_jobs() -> List[Dict]:
    """
    this returns a list of dicts so it can be properly parsed and defaults would be set
    """
    # deepcopy = list and dict are mutable, we want to make sure
    # no one will mutate the default jobs (hello tests)
    return deepcopy(
        [
            {
                "job": "copr_build",
                "trigger": "pull_request",
                "targets": [DEFAULT_VERSION],
            },
            {
                "job": "tests",
                "trigger": "pull_request",
                "targets": [DEFAULT_VERSION],
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "dist_git_branches": ["fedora-all"],
            },
        ]
    )
