# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from copy import deepcopy
from enum import Enum
from logging import getLogger
from typing import List, Dict, Optional, Union, Any

from packit.actions import ActionName
from packit.config.aliases import DEFAULT_VERSION
from packit.config.common_package_config import CommonPackageConfig, Deployment
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
    bodhi_update = "bodhi_update"


class JobConfigTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"


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
        config_file_path: Optional[str] = None,
        specfile_path: Optional[str] = None,
        synced_files: Optional[List[SyncFilesItem]] = None,
        files_to_sync: Optional[List[SyncFilesItem]] = None,
        dist_git_namespace: Optional[str] = None,
        upstream_project_url: Optional[str] = None,  # can be URL or path
        upstream_package_name: Optional[str] = None,
        downstream_project_url: Optional[str] = None,
        downstream_package_name: Optional[str] = None,
        dist_git_base_url: Optional[str] = None,
        actions: Optional[Dict[ActionName, Union[str, List[str]]]] = None,
        upstream_ref: Optional[str] = None,
        allowed_gpg_keys: Optional[List[str]] = None,
        create_pr: bool = True,
        sync_changelog: bool = False,
        create_sync_note: bool = True,
        spec_source_id: str = "Source0",
        upstream_tag_template: str = "{version}",
        archive_root_dir_template: str = "{upstream_pkg_name}-{version}",
        patch_generation_ignore_paths: Optional[List[str]] = None,
        patch_generation_patch_id_digits: int = 4,
        notifications: Optional[NotificationsConfig] = None,
        copy_upstream_release_description: bool = False,
        sources: Optional[List[SourcesItem]] = None,
        merge_pr_in_ci: bool = True,
        srpm_build_deps: Optional[List[str]] = None,
        identifier: Optional[str] = None,
        packit_instances: Optional[List[Deployment]] = None,
        issue_repository: Optional[str] = None,
        release_suffix: Optional[str] = None,
        # from deprecated JobMetadataConfig
        _targets: Union[List[str], Dict[str, Dict[str, Any]], None] = None,
        timeout: int = 7200,
        owner: Optional[str] = None,
        project: Optional[str] = None,
        dist_git_branches: Optional[List[str]] = None,
        branch: Optional[str] = None,
        scratch: bool = False,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: Optional[List[str]] = None,
        additional_repos: Optional[List[str]] = None,
        fmf_url: Optional[str] = None,
        fmf_ref: Optional[str] = None,
        use_internal_tf: bool = False,
        skip_build: bool = False,
        env: Optional[Dict[str, Any]] = None,
        enable_net: bool = True,
        allowed_pr_authors: Optional[List[str]] = None,
        allowed_committers: Optional[List[str]] = None,
    ):
        super().__init__(
            config_file_path=config_file_path,
            specfile_path=specfile_path,
            synced_files=synced_files,
            files_to_sync=files_to_sync,
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
            create_sync_note=create_sync_note,
            spec_source_id=spec_source_id,
            upstream_tag_template=upstream_tag_template,
            archive_root_dir_template=archive_root_dir_template,
            patch_generation_ignore_paths=patch_generation_ignore_paths,
            patch_generation_patch_id_digits=patch_generation_patch_id_digits,
            notifications=notifications,
            copy_upstream_release_description=copy_upstream_release_description,
            sources=sources,
            merge_pr_in_ci=merge_pr_in_ci,
            srpm_build_deps=srpm_build_deps,
            identifier=identifier,
            packit_instances=packit_instances,
            issue_repository=issue_repository,
            release_suffix=release_suffix,
            # from deprecated JobMetadataConfig
            _targets=_targets,
            timeout=timeout,
            owner=owner,
            project=project,
            dist_git_branches=dist_git_branches,
            branch=branch,
            scratch=scratch,
            list_on_homepage=list_on_homepage,
            preserve_project=preserve_project,
            additional_packages=additional_packages,
            additional_repos=additional_repos,
            fmf_url=fmf_url,
            fmf_ref=fmf_ref,
            use_internal_tf=use_internal_tf,
            skip_build=skip_build,
            env=env,
            enable_net=enable_net,
            allowed_pr_authors=allowed_pr_authors,
            allowed_committers=allowed_committers,
        )
        self.type: JobType = type
        self.trigger: JobConfigTriggerType = trigger

    def __repr__(self):
        return (
            f"JobConfig(job={self.type}, trigger={self.trigger}, "
            f"config_file_path='{self.config_file_path}', "
            f"specfile_path='{self.specfile_path}', "
            f"files_to_sync='{self.files_to_sync}', "
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
            f"create_sync_note='{self.create_sync_note}', "
            f"spec_source_id='{self.spec_source_id}', "
            f"upstream_tag_template='{self.upstream_tag_template}', "
            f"patch_generation_ignore_paths='{self.patch_generation_ignore_paths}',"
            f"patch_generation_patch_id_digits='{self.patch_generation_patch_id_digits}',"
            f"copy_upstream_release_description='{self.copy_upstream_release_description}',"
            f"sources='{self.sources}', "
            f"merge_pr_in_ci={self.merge_pr_in_ci}, "
            f"srpm_build_deps={self.srpm_build_deps}, "
            f"identifier='{self.identifier}', "
            f"packit_instances={self.packit_instances}, "
            f"issue_repository='{self.issue_repository}', "
            f"release_suffix='{self.release_suffix}', "
            # from deprecated JobMetadataConfig
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
            f"env={self.env},"
            f"enable_net={self.enable_net},"
            f"allowed_pr_authors={self.allowed_pr_authors},"
            f"allowed_commiters={self.allowed_committers})"
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
            and self.specfile_path == other.specfile_path
            and self.files_to_sync == other.files_to_sync
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
            and self.create_sync_note == other.create_sync_note
            and self.spec_source_id == other.spec_source_id
            and self.upstream_tag_template == other.upstream_tag_template
            and self.copy_upstream_release_description
            == other.copy_upstream_release_description
            and self.sources == other.sources
            and self.merge_pr_in_ci == other.merge_pr_in_ci
            and self.srpm_build_deps == other.srpm_build_deps
            and self.identifier == other.identifier
            and self.packit_instances == other.packit_instances
            and self.issue_repository == other.issue_repository
            and self.release_suffix == other.release_suffix
            and self._targets == other._targets
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
            and self.enable_net == other.enable_net
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
