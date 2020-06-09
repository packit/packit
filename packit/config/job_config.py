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
from copy import deepcopy
from enum import Enum
from logging import getLogger
from typing import List, Set, Dict, Optional, Union

from packit.actions import ActionName
from packit.config.common_package_config import CommonPackageConfig
from packit.config.notifications import NotificationsConfig
from packit.config.sync_files_config import SyncFilesConfig
from packit.exceptions import PackitConfigException

logger = getLogger(__name__)


class JobType(Enum):
    """ Type of the job to execute: pick the correct handler """

    propose_downstream = "propose_downstream"
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
    create_bugzilla = "create_bugzilla"


class JobConfigTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"


class JobMetadataConfig:
    def __init__(
        self,
        targets: List[str] = None,
        timeout: int = 7200,
        owner: str = None,
        project: str = None,
        dist_git_branches: List[str] = None,
        branch: str = None,
        scratch: bool = False,
    ):
        """
        :param targets: copr_build job, mock chroots where to build
        :param timeout: copr_build, give up watching a build after timeout, defaults to 7200s
        :param owner: copr_build, a namespace in COPR where the build should happen
        :param project: copr_build, a name of the copr project
        :param dist_git_branches: propose_downstream, branches in dist-git where packit should work
        :param branch: for `commit` trigger to specify the branch name
        :param scratch: if we want to run scratch build in koji
        """
        self.targets: Set[str] = set(targets) if targets else set()
        self.timeout: int = timeout
        self.owner: str = owner
        self.project: str = project
        self.dist_git_branches: Set[str] = set(
            dist_git_branches
        ) if dist_git_branches else set()
        self.branch: str = branch
        self.scratch: bool = scratch

    def __repr__(self):
        return (
            f"JobMetadataConfig("
            f"targets={self.targets}, "
            f"timeout={self.timeout}, "
            f"owner={self.owner}, "
            f"project={self.project}, "
            f"dist_git_branches={self.dist_git_branches},"
            f"branch={self.branch},"
            f"scratch={self.scratch})"
        )

    def __eq__(self, other: object):
        if not isinstance(other, JobMetadataConfig):
            raise PackitConfigException(
                "Provided object is not a JobMetadataConfig instance."
            )
        return (
            self.targets == other.targets
            and self.timeout == other.timeout
            and self.owner == other.owner
            and self.project == other.project
            and self.dist_git_branches == other.dist_git_branches
            and self.branch == other.branch
            and self.scratch == other.scratch
        )


class JobConfig(CommonPackageConfig):
    """
    Definition of a job.

    We want users to be able to override global attributes per job hence
    this inherits from CommonPackageConfig which contains all the definitions.
    """

    def __init__(
        self,
        type: JobType,
        trigger: JobConfigTriggerType,
        metadata: JobMetadataConfig = None,
        config_file_path: Optional[str] = None,
        specfile_path: Optional[str] = None,
        synced_files: Optional[SyncFilesConfig] = None,
        dist_git_namespace: str = None,
        upstream_project_url: str = None,  # can be URL or path
        upstream_package_name: str = None,
        downstream_project_url: str = None,
        downstream_package_name: str = None,
        dist_git_base_url: str = None,
        create_tarball_command: List[str] = None,
        current_version_command: List[str] = None,
        actions: Dict[ActionName, Union[str, List[str]]] = None,
        upstream_ref: Optional[str] = None,
        allowed_gpg_keys: Optional[List[str]] = None,
        create_pr: bool = True,
        spec_source_id: str = "Source0",
        upstream_tag_template: str = "{version}",
        patch_generation_ignore_paths: List[str] = None,
        notifications: Optional[NotificationsConfig] = None,
    ):
        super().__init__(
            config_file_path=config_file_path,
            specfile_path=specfile_path,
            synced_files=synced_files,
            dist_git_namespace=dist_git_namespace,
            upstream_project_url=upstream_project_url,
            upstream_package_name=upstream_package_name,
            downstream_project_url=downstream_project_url,
            downstream_package_name=downstream_package_name,
            dist_git_base_url=dist_git_base_url,
            create_tarball_command=create_tarball_command,
            current_version_command=current_version_command,
            actions=actions,
            upstream_ref=upstream_ref,
            allowed_gpg_keys=allowed_gpg_keys,
            create_pr=create_pr,
            spec_source_id=spec_source_id,
            upstream_tag_template=upstream_tag_template,
            patch_generation_ignore_paths=patch_generation_ignore_paths,
            notifications=notifications,
        )
        self.type: JobType = type
        self.trigger: JobConfigTriggerType = trigger
        self.metadata: JobMetadataConfig = metadata or JobMetadataConfig()

    def __repr__(self):
        return (
            f"JobConfig(job={self.type}, trigger={self.trigger}, meta={self.metadata}, "
            f"config_file_path='{self.config_file_path}', "
            f"specfile_path='{self.specfile_path}', "
            f"synced_files='{self.synced_files}', "
            f"dist_git_namespace='{self.dist_git_namespace}', "
            f"upstream_project_url='{self.upstream_project_url}', "
            f"upstream_package_name='{self.upstream_package_name}', "
            f"downstream_project_url='{self.downstream_project_url}', "
            f"downstream_package_name='{self.downstream_package_name}', "
            f"dist_git_base_url='{self.dist_git_base_url}', "
            f"create_tarball_command='{self.create_tarball_command}', "
            f"current_version_command='{self.current_version_command}', "
            f"actions='{self.actions}', "
            f"upstream_ref='{self.upstream_ref}', "
            f"allowed_gpg_keys='{self.allowed_gpg_keys}', "
            f"create_pr='{self.create_pr}', "
            f"spec_source_id='{self.spec_source_id}', "
            f"upstream_tag_template='{self.upstream_tag_template}', "
            f"patch_generation_ignore_paths='{self.patch_generation_ignore_paths}')"
        )

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "JobConfig":
        # required to avoid cyclical imports
        from packit.schema import JobConfigSchema

        config = JobConfigSchema().load_config(raw_dict)
        logger.debug(f"Loaded config: {config}")

        return config

    def __eq__(self, other: object):
        if not isinstance(other, JobConfig):
            raise PackitConfigException("Provided object is not a JobConfig instance.")
        return (
            self.type == other.type
            and self.trigger == other.trigger
            and self.metadata == other.metadata
            and self.specfile_path == other.specfile_path
            and self.synced_files == other.synced_files
            and self.dist_git_namespace == other.dist_git_namespace
            and self.upstream_project_url == other.upstream_project_url
            and self.upstream_package_name == other.upstream_package_name
            and self.downstream_project_url == other.downstream_project_url
            and self.downstream_package_name == other.downstream_package_name
            and self.dist_git_base_url == other.dist_git_base_url
            and self.current_version_command == other.current_version_command
            and self.create_tarball_command == other.create_tarball_command
            and self.actions == other.actions
            and self.allowed_gpg_keys == other.allowed_gpg_keys
            and self.create_pr == other.create_pr
            and self.spec_source_id == other.spec_source_id
            and self.upstream_tag_template == other.upstream_tag_template
        )


def get_default_jobs() -> List[Dict]:
    """
    this returns a list of dicts so it can be properly parsed and defaults would be set
    """
    # deepcopy = list and dict are mutable, we want to make sure
    # no one will mutate the default jobs (hello tests)
    return deepcopy(
        [
            {
                "job": "tests",
                "trigger": "pull_request",
                "metadata": {"targets": "fedora-stable"},
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "metadata": {"dist_git_branches": "fedora-all"},
            },
        ]
    )
