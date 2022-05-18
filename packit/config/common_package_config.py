# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Common package config attributes so they can be imported both in PackageConfig and JobConfig
"""
import warnings
import logging
from enum import Enum

from os import getenv
from os.path import basename
from typing import Dict, List, Optional, Union, Any, Set

from packit.actions import ActionName
from packit.config.notifications import (
    NotificationsConfig,
    PullRequestNotificationsConfig,
)
from packit.config.sources import SourcesItem
from packit.constants import PROD_DISTGIT_URL, DISTGIT_NAMESPACE
from packit.sync import SyncFilesItem, iter_srcs


class Deployment(Enum):
    dev = "dev"
    stg = "stg"
    prod = "prod"


class CommonPackageConfig:
    """
    We want JobConfig to hold all the attributes from PackageConfig so we don't need to
    pass both PackageConfig and JobConfig to handlers in p-s. We also want people
    to be able to override global PackageConfig attributes per job.

                        CommonPackageConfig
                              /      \
                   PackageConfig   JobConfig
                          //
              contains [JobConfig]

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
        enable_net: if set to False, Copr builds have network disabled
        allowed_pr_authors: list of Fedora accounts for which distgit PRs we
                        will run koji builds
        allowed_committers: list of Fedora accounts for which distgit pushes we
                        will run koji builds
    """

    def __init__(
        self,
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
        actions: Dict[ActionName, Union[str, List[str]]] = None,
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
        self.config_file_path: Optional[str] = config_file_path
        self.specfile_path: Optional[str] = specfile_path

        self._files_to_sync: List[SyncFilesItem] = files_to_sync or []  # new option
        self._files_to_sync_used: bool = False if files_to_sync is None else True
        self.synced_files: List[SyncFilesItem] = (
            synced_files or []
        )  # old deprecated option
        if synced_files is not None:
            self._warn_user()

        self.patch_generation_ignore_paths = patch_generation_ignore_paths or []
        self.patch_generation_patch_id_digits = patch_generation_patch_id_digits
        self.upstream_project_url: Optional[str] = upstream_project_url
        self.upstream_package_name: Optional[str] = upstream_package_name
        # this is generated by us
        self.downstream_package_name: Optional[str] = downstream_package_name
        self._downstream_project_url: str = downstream_project_url
        self.dist_git_base_url: str = dist_git_base_url or getenv(
            "DISTGIT_URL", PROD_DISTGIT_URL
        )
        self.dist_git_namespace: str = dist_git_namespace or getenv(
            "DISTGIT_NAMESPACE", DISTGIT_NAMESPACE
        )
        # path to a local git clone of the dist-git repo; None means to clone in a tmpdir
        self.dist_git_clone_path: Optional[str] = None
        self.actions = actions or {}
        self.upstream_ref: Optional[str] = upstream_ref
        self.allowed_gpg_keys = allowed_gpg_keys
        self.create_pr: bool = create_pr
        self.sync_changelog: bool = sync_changelog
        self.create_sync_note: bool = create_sync_note
        self.spec_source_id: str = spec_source_id
        self.notifications = notifications or NotificationsConfig(
            pull_request=PullRequestNotificationsConfig()
        )
        self.identifier = identifier

        # The default is set also on schema level,
        # but for sake of code-generated configs,
        # we want to react on prod events only by default.
        self.packit_instances = (
            packit_instances if packit_instances is not None else [Deployment.prod]
        )

        # template to create an upstream tag name (upstream may use different tagging scheme)
        self.upstream_tag_template = upstream_tag_template
        self.archive_root_dir_template = archive_root_dir_template
        self.copy_upstream_release_description = copy_upstream_release_description
        self.sources = sources or []
        self.merge_pr_in_ci = merge_pr_in_ci
        self.srpm_build_deps = srpm_build_deps
        self.issue_repository = issue_repository
        self.release_suffix = release_suffix

        # from deprecated JobMetadataConfig
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
        self.enable_net = enable_net
        self.allowed_pr_authors = (
            allowed_pr_authors if allowed_pr_authors is not None else ["packit"]
        )
        self.allowed_committers = allowed_committers or []

    @property
    def targets_dict(self):
        return self._targets

    @property
    def targets(self):
        """For backward compatibility."""
        return set(self._targets.keys())

    def _warn_user(self):
        logger = logging.getLogger(__name__)
        msg = "synced_files option is deprecated. Use files_to_sync option instead."
        logger.warning(msg)
        warnings.warn(msg, DeprecationWarning)
        if self._files_to_sync_used:
            logger.warning(
                "You are setting both files_to_sync and synced_files."
                " Packit will use files_to_sync. You should remove "
                "synced_files since it is deprecated."
            )

    @property
    def files_to_sync(self) -> List[SyncFilesItem]:
        """
        synced_files is the old option we want to deprecate.
        Spec file and configuration file can be automatically added to
        the list of synced_files (see get_all_files_to_sync method)

        files_to_sync is the new option. Files to be synced are just those listed here.
        Spec file and configuration file will not be automatically added
        to the list of files_to_sync (see get_all_files_to_sync method).

        files_to_sync has precedence over synced_files.

        Once the old option will be removed this method can be removed as well.
        """

        if self._files_to_sync_used:
            return self._files_to_sync
        elif self.synced_files:
            return self.synced_files
        else:
            return []

    def __repr__(self):
        return (
            "CommonPackageConfig("
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
            f"create_sync_note='{self.create_sync_note}', "
            f"spec_source_id='{self.spec_source_id}', "
            f"upstream_tag_template='{self.upstream_tag_template}', "
            f"patch_generation_ignore_paths='{self.patch_generation_ignore_paths}',"
            f"patch_generation_patch_id_digits='{self.patch_generation_patch_id_digits}',"
            f"copy_upstream_release_description='{self.copy_upstream_release_description}',"
            f"sources='{self.sources}', "
            f"merge_pr_in_ci={self.merge_pr_in_ci}, "
            f"srpm_build_deps={self.srpm_build_deps}, "
            f"identifier={self.identifier}, "
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
            f"allowed_committers={self.allowed_committers})"
        )

    @property
    def downstream_project_url(self) -> str:
        if not self._downstream_project_url:
            self._downstream_project_url = self.dist_git_package_url
        return self._downstream_project_url

    @property
    def dist_git_package_url(self):
        if self.downstream_package_name:
            return (
                f"{self.dist_git_base_url}{self.dist_git_namespace}/"
                f"{self.downstream_package_name}.git"
            )

    def get_specfile_sync_files_item(self, from_downstream: bool = False):
        """
        Get SyncFilesItem object for the specfile.
        :param from_downstream: True when syncing from downstream
        :return: SyncFilesItem
        """
        upstream_specfile_path = self.specfile_path
        downstream_specfile_path = (
            f"{self.downstream_package_name}.spec"
            if self.downstream_package_name
            else basename(upstream_specfile_path)
        )
        return SyncFilesItem(
            src=[
                downstream_specfile_path if from_downstream else upstream_specfile_path
            ],
            dest=upstream_specfile_path
            if from_downstream
            else downstream_specfile_path,
        )

    def get_all_files_to_sync(self):
        """
        Adds the default files (config file, spec file) to synced files
        if the new files_to_sync option is not yet used otherwise
        do not performer any addition to the list of files to be synced.

        When the old option will be removed this method could be removed as well.

        :return: Files to be synced
        """
        files = self.files_to_sync

        if not self._files_to_sync_used:
            if self.specfile_path not in iter_srcs(files):
                files.append(self.get_specfile_sync_files_item())

            if self.config_file_path and self.config_file_path not in iter_srcs(files):
                # this relative because of glob: "Non-relative patterns are unsupported"
                files.append(
                    SyncFilesItem(
                        src=[self.config_file_path], dest=self.config_file_path
                    )
                )

        return files
