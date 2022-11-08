# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from typing import Callable, Optional, List, Dict, Union, Set

from ogr.abstract import GitProject
from ogr.exceptions import GithubAppNotInstalledError
from yaml import safe_load, YAMLError

from packit.config.common_package_config import CommonPackageConfig, MultiplePackages
from packit.config.job_config import JobConfig, JobType
from packit.constants import CONFIG_FILE_NAMES
from packit.exceptions import PackitConfigException

logger = logging.getLogger(__name__)


class PackageConfig(MultiplePackages):
    """
    Config class capturing the configuration of a upstream or
    downstream repository, aka "packit.yaml"

    Attributes:
        jobs: List of job configs.
    """

    def __init__(
        self,
        packages: Dict[str, CommonPackageConfig],
        jobs: Optional[List[JobConfig]] = None,
    ):
        super().__init__(packages)
        # Directly manipulating __dict__ is not recommended.
        # It is done here to avoid triggering __setattr__ and
        # should be removed once support for a single package is
        # dropped from config objects.
        self.__dict__["jobs"] = jobs or []

    def __repr__(self):
        # required to avoid cyclical imports
        from packit.schema import PackageConfigSchema

        s = PackageConfigSchema()
        # For __repr__() return a JSON-encoded string, by using dumps().
        # Mind the 's'!
        return f"PackageConfig: {s.dumps(self)}"

    @classmethod
    def get_from_dict(
        cls,
        raw_dict: dict,
        config_file_path: Optional[str] = None,
        repo_name: Optional[str] = None,
        search_specfile: Optional[Callable[..., Optional[str]]] = None,
        **specfile_search_args,
    ) -> "PackageConfig":
        # required to avoid cyclical imports
        from packit.schema import PackageConfigSchema

        # we need to process defaults first so they get propagated to JobConfigs

        raw_dict.setdefault("config_file_path", config_file_path)

        if not raw_dict.get("specfile_path"):
            default_specfile_path = None
            # we default to <downstream_package_name>.spec
            # https://packit.dev/docs/configuration/#specfile_path
            if downstream_package_name := raw_dict.get("downstream_package_name", None):
                default_specfile_path = f"{downstream_package_name}.spec"
            elif search_specfile:
                default_specfile_path = search_specfile(**specfile_search_args)
            raw_dict["specfile_path"] = default_specfile_path

        # Do this _after_ setting the default for 'specfile_path',
        # so that 'downstream_package_name' is considered for setting
        # 'specfile_path' _only_ when set in packit.yaml.
        if repo_name:
            raw_dict.setdefault("upstream_package_name", repo_name)
            raw_dict.setdefault("downstream_package_name", repo_name)

        package_config = PackageConfigSchema().load(raw_dict)

        return package_config

    def get_copr_build_project_value(self) -> Optional[str]:
        """
        get copr project name from this first copr job
        this is only used when invoking copr builds from CLI
        """
        projects_list = [
            job.project
            for job in self.jobs
            if job.type == JobType.copr_build and job.project
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
                return job.dist_git_branches
        return set()

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            return NotImplemented
        # required to avoid cyclical imports
        from packit.schema import PackageConfigSchema

        s = PackageConfigSchema()
        # Compare the serialized objects.
        serialized_self = s.dump(self)
        serialized_other = s.dump(other)
        logger.debug(f"our configuration:\n{serialized_self}")
        logger.debug(f"the other configuration:\n{serialized_other}")
        return serialized_self == serialized_other


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


def load_packit_yaml(
    config_file_path: Optional[Path] = None, raw_text: str = ""
) -> Dict:
    """
    Use yaml.safe_load to parse provided text as yaml

    When config_file_path is set, read the file, otherwise process content of raw_text.

    Args:
        config_file_path: local path to .packit.yaml
        raw_text: content of .packit.yaml

    Raises:
        PackitConfigException when something goes wrong while loading the config

    Returns:
        Dict with the file content
    """
    if config_file_path:
        raw_text = config_file_path.read_text()
    try:
        # safe_load() returns None when the file is empty, but this needs
        # to return a dict.
        return safe_load(raw_text) or {}
    except YAMLError as ex:
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

    loaded_config = load_packit_yaml(config_file_path=config_file_name)

    return parse_loaded_config(
        loaded_config=loaded_config,
        config_file_path=config_file_name.name,
        repo_name=repo_name,
        search_specfile=get_local_specfile_path,
        dir=config_file_name.parent,
    )


def get_package_config_from_repo(
    project: GitProject,
    ref: Optional[str] = None,
) -> Optional[PackageConfig]:
    for config_file_name in CONFIG_FILE_NAMES:
        try:
            config_file_content = project.get_file_content(
                path=config_file_name, ref=ref
            )
        except (FileNotFoundError, GithubAppNotInstalledError):
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

    loaded_config = load_packit_yaml(raw_text=config_file_content)

    return parse_loaded_config(
        loaded_config=loaded_config,
        config_file_path=config_file_name,
        repo_name=project.repo,
        search_specfile=get_specfile_path_from_repo,
        project=project,
        ref=ref,
    )


def parse_loaded_config(
    loaded_config: dict,
    config_file_path: Optional[str] = None,
    repo_name: Optional[str] = None,
    spec_file_path: Optional[str] = None,
    search_specfile: Optional[Callable[..., Optional[str]]] = None,
    **specfile_search_args,
) -> PackageConfig:
    """Tries to parse the config to PackageConfig."""
    logger.debug(
        f"Package config before loading:\n{json.dumps(loaded_config, indent=4)}"
    )

    try:
        return PackageConfig.get_from_dict(
            raw_dict=loaded_config,
            config_file_path=config_file_path,
            repo_name=repo_name,
            search_specfile=search_specfile,
            **specfile_search_args,
        )
    except Exception as ex:
        logger.error(f"Cannot parse package config. {ex}.")
        raise PackitConfigException(f"Cannot parse package config: {ex!r}.")


def get_local_specfile_path(dir: Path, exclude: List[str] = None) -> Optional[str]:
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

    # Don't take files found in exclude
    sexclude = set(exclude) if exclude else {"tests"}
    files = [f for f in files if f.parts[0] not in sexclude]

    if len(files) > 0:
        logger.debug(f"Local spec files found: {files}. Taking: {files[0]}")
        return str(files[0])

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
