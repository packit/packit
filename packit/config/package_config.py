# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union, Set

from ogr.abstract import GitProject
from yaml import safe_load

from packit.actions import ActionName
from packit.config.common_package_config import CommonPackageConfig
from packit.config.job_config import JobConfig, get_default_jobs, JobType
from packit.config.notifications import NotificationsConfig
from packit.config.sources import SourcesItem
from packit.sync import SyncFilesItem
from packit.constants import CONFIG_FILE_NAMES
from packit.exceptions import PackitConfigException

logger = logging.getLogger(__name__)


class PackageConfig(CommonPackageConfig):
    """
    Config class for upstream/downstream packages;
    this is the config people put in their repos
    """

    def __init__(
        self,
        config_file_path: Optional[str] = None,
        specfile_path: Optional[str] = None,
        synced_files: Optional[List[SyncFilesItem]] = None,
        files_to_sync: Optional[List[SyncFilesItem]] = None,
        jobs: Optional[List[JobConfig]] = None,
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
        create_sync_note: bool = True,
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
        )
        self.jobs: List[JobConfig] = jobs or []

    def __repr__(self):
        return (
            "PackageConfig("
            f"config_file_path='{self.config_file_path}', "
            f"specfile_path='{self.specfile_path}', "
            f"files_to_sync='{self.files_to_sync}', "
            f"jobs='{self.jobs}', "
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
            f"archive_root_dir_template={self.archive_root_dir_template}', "
            f"patch_generation_ignore_paths='{self.patch_generation_ignore_paths}', "
            f"patch_generation_patch_id_digits='{self.patch_generation_patch_id_digits}', "
            f"copy_upstream_release_description='{self.copy_upstream_release_description}',"
            f"sources='{self.sources}', "
            f"merge_pr_in_ci={self.merge_pr_in_ci})"
        )

    @classmethod
    def get_from_dict(
        cls,
        raw_dict: dict,
        config_file_path: str = None,
        repo_name: str = None,
        spec_file_path: str = None,
    ) -> "PackageConfig":
        # required to avoid cyclical imports
        from packit.schema import PackageConfigSchema

        if config_file_path and not raw_dict.get("config_file_path", None):
            raw_dict.update(config_file_path=config_file_path)

        # we need to process defaults first so they get propagated to JobConfigs

        if "jobs" not in raw_dict:
            # we want default jobs to go through the proper parsing process
            raw_dict["jobs"] = get_default_jobs()

        if not raw_dict.get("specfile_path", None) and spec_file_path:
            raw_dict["specfile_path"] = spec_file_path

        if not raw_dict.get("upstream_package_name", None) and repo_name:
            raw_dict["upstream_package_name"] = repo_name

        if not raw_dict.get("downstream_package_name", None) and repo_name:
            raw_dict["downstream_package_name"] = repo_name

        package_config = PackageConfigSchema().load(raw_dict)

        if not package_config.specfile_path and not all(
            job.type == JobType.tests and job.metadata.skip_build
            for job in package_config.jobs
        ):
            raise PackitConfigException("Spec file was not found!")

        return package_config

    def get_copr_build_project_value(self) -> Optional[str]:
        """
        get copr project name from this first copr job
        this is only used when invoking copr builds from CLI
        """
        projects_list = [
            job.metadata.project
            for job in self.jobs
            if job.type == JobType.copr_build and job.metadata.project
        ]
        if not projects_list:
            return None

        if len(set(projects_list)) > 1:
            logger.warning(
                f"You have defined multiple copr projects to build in, we are going "
                f"to pick the first one: {projects_list[0]}, reorder the job definitions"
                f" if this is not the one you want."
            )
        return projects_list[0]

    def get_propose_downstream_dg_branches_value(self) -> Optional[Set]:
        for job in self.jobs:
            if job.type == JobType.propose_downstream:
                return job.metadata.dist_git_branches
        return set()

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            return NotImplemented
        logger.debug(f"our configuration:\n{self.__dict__}")
        logger.debug(f"the other configuration:\n{other.__dict__}")
        return (
            self.specfile_path == other.specfile_path
            and self.files_to_sync == other.files_to_sync
            and self.jobs == other.jobs
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
        )


def find_packit_yaml(
    *directory: Union[Path, str],
    try_local_dir_first: bool = False,
    try_local_dir_last: bool = False,
) -> Path:
    """
    find packit.yaml in provided directories: if a file matches, it's picked
    if no config is found, raise PackitConfigException

    :param directory: a list of dirs where we should find
    :param try_local_dir_first: try in cwd first
    :param try_local_dir_last: try cwd last
    :return: Path to the config
    """
    directories = [Path(config_dir) for config_dir in directory]
    cwd = Path.cwd()

    if try_local_dir_first and try_local_dir_last:
        logger.error(
            "Ambiguous usage of 'try_local_dir_first' and 'try_local_dir_last'."
        )

    if try_local_dir_first:
        if cwd in directories:
            directories.remove(cwd)
        directories.insert(0, cwd)

    if try_local_dir_last:
        if cwd in directories:
            directories.remove(cwd)
        directories.append(cwd)

    for config_dir in directories:
        for config_file_name in CONFIG_FILE_NAMES:
            config_file_name_full = config_dir / config_file_name
            if config_file_name_full.is_file():
                logger.debug(f"Local package config found: {config_file_name_full}")
                return config_file_name_full
    raise PackitConfigException("No packit config found.")


def load_packit_yaml(config_file_path: Path) -> Dict:
    """
    load provided packit.yaml, raise PackitConfigException if something is wrong

    :return: Dict with the file content
    """
    try:
        return safe_load(config_file_path.read_text())
    except Exception as ex:
        logger.error(f"Cannot load package config {config_file_path}.")
        raise PackitConfigException(f"Cannot load package config: {ex!r}.")


def get_local_package_config(
    *directory: Union[Path, str],
    repo_name: Optional[str] = None,
    try_local_dir_first: bool = False,
    try_local_dir_last: bool = False,
    package_config_path: Optional[str] = None,
) -> PackageConfig:
    """
    find packit.yaml in provided dirs, load it and return PackageConfig

    :param directory: a list of dirs where we should find
    :param repo_name: name of the git repository (default for project name)
    :param try_local_dir_first: try in cwd first
    :param try_local_dir_last: try cwd last
    :param package_config_path: Path to package configuration file
    :return: local PackageConfig
    """

    if package_config_path:
        config_file_name = Path(package_config_path)
    else:
        config_file_name = find_packit_yaml(
            *directory,
            try_local_dir_first=try_local_dir_first,
            try_local_dir_last=try_local_dir_last,
        )

    loaded_config = load_packit_yaml(config_file_name)
    return parse_loaded_config(
        loaded_config=loaded_config,
        config_file_path=config_file_name.name,
        repo_name=repo_name,
        spec_file_path=str(get_local_specfile_path(config_file_name.parent)),
    )


def get_package_config_from_repo(
    project: GitProject, ref: str = None, spec_file_path: Optional[str] = None
) -> Optional[PackageConfig]:
    for config_file_name in CONFIG_FILE_NAMES:
        try:
            config_file_content = project.get_file_content(
                path=config_file_name, ref=ref
            )
        except FileNotFoundError:
            # do nothing
            pass
        else:
            logger.debug(
                f"Found a config file {config_file_name!r} "
                f"on ref {ref!r} "
                f"of the {project.full_repo_name!r} repository."
            )
            break
    else:
        logger.warning(
            f"No config file ({CONFIG_FILE_NAMES}) found on ref {ref!r} "
            f"of the {project.full_repo_name!r} repository."
        )
        return None

    try:
        loaded_config = safe_load(config_file_content)
    except Exception as ex:
        logger.error(f"Cannot load package config {config_file_name!r}. {ex}")
        raise PackitConfigException(
            f"Cannot load package config {config_file_name!r}. {ex}"
        )
    if not spec_file_path:
        logger.warning(f"Spec file path is not specified in {config_file_name}.")
        spec_file_path = get_specfile_path_from_repo(project=project, ref=ref)

    return parse_loaded_config(
        loaded_config=loaded_config,
        config_file_path=config_file_name,
        repo_name=project.repo,
        spec_file_path=spec_file_path,
    )


def parse_loaded_config(
    loaded_config: dict,
    config_file_path: Optional[str] = None,
    repo_name: Optional[str] = None,
    spec_file_path: Optional[str] = None,
) -> PackageConfig:
    """Tries to parse the config to PackageConfig."""
    logger.debug(f"Package config:\n{json.dumps(loaded_config, indent=4)}")

    try:
        return PackageConfig.get_from_dict(
            raw_dict=loaded_config,
            config_file_path=config_file_path,
            repo_name=repo_name,
            spec_file_path=spec_file_path,
        )
    except Exception as ex:
        logger.error(f"Cannot parse package config. {ex}.")
        raise PackitConfigException(f"Cannot parse package config: {ex!r}.")


def get_local_specfile_path(dir: Path, exclude: List[str] = None) -> Optional[Path]:
    """
    Get the path (relative to dir) of the local spec file if present.
    If the spec is not found in dir directly, try to search it recursively (rglob)
    :param dir: to find the spec file in
    :param exclude: don't include files found in these dirs (default "tests")
    :return: path (relative to dir) of the first found spec file
    """
    files = [path.relative_to(dir) for path in dir.glob("*.spec")] or [
        path.relative_to(dir) for path in dir.rglob("*.spec")
    ]

    if len(files) > 0:
        # Don't take files found in exclude
        sexclude = set(exclude) if exclude else {"tests"}
        files = [f for f in files if f.parts[0] not in sexclude]

        logger.debug(f"Local spec files found: {files}. Taking: {files[0]}")
        return files[0]

    return None


def get_specfile_path_from_repo(project: GitProject, ref: str = None) -> Optional[str]:
    """
    Get the path of the spec file in the given repo if present.
    :param project: GitProject
    :param ref: git ref (defaults to repo's default branch)
    :return: str path of the spec file or None
    """
    spec_files = project.get_files(ref=ref, filter_regex=r".+\.spec$")

    if not spec_files:
        logger.debug(f"No spec file found in {project.full_repo_name!r}")
        return None
    return spec_files[0]
