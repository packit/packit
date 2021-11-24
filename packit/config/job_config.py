# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from copy import deepcopy
from enum import Enum
from logging import getLogger
from typing import List, Set, Dict, Optional, Union, Any

from packit.actions import ActionName
from packit.config.aliases import DEFAULT_VERSION
from packit.config.common_package_config import CommonPackageConfig
from packit.config.notifications import NotificationsConfig
from packit.config.sources import SourcesItem
from packit.sync import SyncFilesItem
from packit.exceptions import PackitConfigException

logger = getLogger(__name__)


class JobType(Enum):
    """Type of the job used by users in the config"""

    propose_downstream = "propose_downstream"
    build = "build"
    sync_from_downstream = "sync_from_downstream"
    copr_build = "copr_build"
    production_build = "production_build"  # upstream koji build
    koji_build = "koji_build"  # downstream koji build
    tests = "tests"


class JobConfigTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"


class JobMetadataConfig:
    def __init__(
        self,
        _targets: Union[List[str], Dict[str, Dict[str, Any]]] = None,
        timeout: int = 7200,
        owner: str = None,
        project: str = None,
        dist_git_branches: List[str] = None,
        branch: str = None,
        scratch: bool = False,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: List[str] = None,
        additional_repos: List[str] = None,
        fmf_url: str = None,
        fmf_ref: str = None,
        use_internal_tf: bool = False,
        skip_build: bool = False,
        env: Dict[str, Any] = None,
    ):
        """
        Args:
            _targets: copr_build, mock chroots where to build
                      tests, builds to test
                      The _ prefix is used because 'targets' without it
                      is now used for backward compatibility.
            timeout: copr_build, give up watching a build after timeout, defaults to 7200s
            owner: copr_build, a namespace in COPR where the build should happen
            project: copr_build, a name of the copr project
            dist_git_branches: propose_downstream, branches in dist-git where packit should work
            branch: for `commit` trigger to specify the branch name
            scratch: if we want to run scratch build in koji
            list_on_homepage: if set, created copr project will be visible on copr's home-page
            preserve_project: if set, project will not be created as temporary
            additional_packages: buildroot packages for the chroot [DOES NOT WORK YET]
            additional_repos: buildroot additional additional_repos
            fmf_url: - git repository containing the metadata (FMF) tree
            fmf_ref: - branch, tag or commit specifying the desired git revision
            use_internal_tf: if we want to use internal instance of Testing Farm
            skip_build: if we want to skip build phase for Testing Farm job
            env: environment variables
        """
        self._targets: Dict[str, Dict[str, Any]]
        if isinstance(_targets, list):
            self._targets = {key: {} for key in _targets}
        else:
            self._targets = _targets or {}
        self.timeout: int = timeout
        self.owner: str = owner
        self.project: str = project
        self.dist_git_branches: Set[str] = (
            set(dist_git_branches) if dist_git_branches else set()
        )
        self.branch: str = branch
        self.scratch: bool = scratch
        self.list_on_homepage: bool = list_on_homepage
        self.preserve_project: bool = preserve_project
        self.additional_packages: List[str] = additional_packages or []
        self.additional_repos: List[str] = additional_repos or []
        self.fmf_url: str = fmf_url
        self.fmf_ref: str = fmf_ref
        self.use_internal_tf: bool = use_internal_tf
        self.skip_build: bool = skip_build
        self.env: Dict[str, Any] = env or {}

    def __repr__(self):
        return (
            f"JobMetadataConfig("
            f"targets={self._targets}, "
            f"timeout={self.timeout}, "
            f"owner={self.owner}, "
            f"project={self.project}, "
            f"dist_git_branches={self.dist_git_branches}, "
            f"branch={self.branch}, "
            f"scratch={self.scratch}, "
            f"list_on_homepage={self.list_on_homepage}, "
            f"preserve_project={self.preserve_project}, "
            f"additional_packages={self.additional_packages}, "
            f"additional_repos={self.additional_repos}, "
            f"fmf_url={self.fmf_url}, "
            f"fmf_ref={self.fmf_ref}, "
            f"use_internal_tf={self.use_internal_tf}, "
            f"skip_build={self.skip_build},"
            f"env={self.env})"
        )

    def __eq__(self, other: object):
        if not isinstance(other, JobMetadataConfig):
            raise PackitConfigException(
                "Provided object is not a JobMetadataConfig instance."
            )
        return (
            self._targets == other._targets
            and self.timeout == other.timeout
            and self.owner == other.owner
            and self.project == other.project
            and self.dist_git_branches == other.dist_git_branches
            and self.branch == other.branch
            and self.scratch == other.scratch
            and self.list_on_homepage == other.list_on_homepage
            and self.preserve_project == other.preserve_project
            and self.additional_packages == other.additional_packages
            and self.additional_repos == other.additional_repos
            and self.fmf_url == other.fmf_url
            and self.fmf_ref == other.fmf_ref
            and self.use_internal_tf == other.use_internal_tf
            and self.skip_build == other.skip_build
            and self.env == other.env
        )

    @property
    def targets_dict(self):
        return self._targets

    @property
    def targets(self):
        """For backward compatibility."""
        return set(self._targets.keys())


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
        synced_files: Optional[List[SyncFilesItem]] = None,
        dist_git_namespace: str = None,
        upstream_project_url: str = None,  # can be URL or path
        upstream_package_name: str = None,
        downstream_project_url: str = None,
        downstream_package_name: str = None,
        dist_git_base_url: str = None,
        actions: Dict[ActionName, Union[str, List[str]]] = None,
        upstream_ref: Optional[str] = None,
        allowed_gpg_keys: Optional[List[str]] = None,
        create_pr: bool = True,
        sync_changelog: bool = False,
        spec_source_id: str = "Source0",
        upstream_tag_template: str = "{version}",
        archive_root_dir_template: str = "{upstream_pkg_name}-{version}",
        patch_generation_ignore_paths: List[str] = None,
        patch_generation_patch_id_digits: int = 4,
        notifications: Optional[NotificationsConfig] = None,
        copy_upstream_release_description: bool = False,
        sources: Optional[List[SourcesItem]] = None,
        merge_pr_in_ci: bool = True,
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
            actions=actions,
            upstream_ref=upstream_ref,
            allowed_gpg_keys=allowed_gpg_keys,
            create_pr=create_pr,
            sync_changelog=sync_changelog,
            spec_source_id=spec_source_id,
            upstream_tag_template=upstream_tag_template,
            archive_root_dir_template=archive_root_dir_template,
            patch_generation_ignore_paths=patch_generation_ignore_paths,
            patch_generation_patch_id_digits=patch_generation_patch_id_digits,
            notifications=notifications,
            copy_upstream_release_description=copy_upstream_release_description,
            sources=sources,
            merge_pr_in_ci=merge_pr_in_ci,
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
            f"actions='{self.actions}', "
            f"upstream_ref='{self.upstream_ref}', "
            f"allowed_gpg_keys='{self.allowed_gpg_keys}', "
            f"create_pr='{self.create_pr}', "
            f"sync_changelog='{self.sync_changelog}', "
            f"spec_source_id='{self.spec_source_id}', "
            f"upstream_tag_template='{self.upstream_tag_template}', "
            f"patch_generation_ignore_paths='{self.patch_generation_ignore_paths}',"
            f"patch_generation_patch_id_digits='{self.patch_generation_patch_id_digits}',"
            f"copy_upstream_release_description='{self.copy_upstream_release_description}',"
            f"sources='{self.sources}', "
            f"merge_pr_in_ci={self.merge_pr_in_ci})"
        )

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
            and self.actions == other.actions
            and self.allowed_gpg_keys == other.allowed_gpg_keys
            and self.create_pr == other.create_pr
            and self.sync_changelog == other.sync_changelog
            and self.spec_source_id == other.spec_source_id
            and self.upstream_tag_template == other.upstream_tag_template
            and self.copy_upstream_release_description
            == other.copy_upstream_release_description
            and self.sources == other.sources
            and self.merge_pr_in_ci == other.merge_pr_in_ci
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
                "job": "copr_build",
                "trigger": "pull_request",
                "metadata": {"targets": [DEFAULT_VERSION]},
            },
            {
                "job": "tests",
                "trigger": "pull_request",
                "metadata": {"targets": [DEFAULT_VERSION]},
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "metadata": {"dist_git_branches": "fedora-all"},
            },
        ]
    )
