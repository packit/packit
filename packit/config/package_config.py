# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from typing import Callable, Optional, Union

from ogr.abstract import GitProject
from ogr.exceptions import (
    APIException,
    GithubAppNotInstalledError,
)
from yaml import YAMLError, safe_load

from packit.config.common_package_config import CommonPackageConfig, MultiplePackages
from packit.config.job_config import (
    JobConfig,
    JobConfigView,
    JobType,
)
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
        packages: dict[str, CommonPackageConfig],
        jobs: Optional[list[JobConfig]] = None,
    ):
        self._job_views: list[Union[JobConfig, JobConfigView]] = []
        self._package_config_views: dict[str, PackageConfigView] = {}
        self._raw_dict_with_defaults: Optional[dict] = None
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
    def set_defaults(
        cls,
        raw_dict: dict,
        repo_name: Optional[str] = None,
        search_specfile: Optional[Callable[..., Optional[str]]] = None,
        **specfile_search_args,
    ) -> None:
        if not raw_dict.get("specfile_path"):
            default_specfile_path = None
            # we default to <downstream_package_name>.spec
            # https://packit.dev/docs/configuration/#specfile_path
            if downstream_package_name := raw_dict.get("downstream_package_name"):
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

        # we need to process defaults first so they get propagated to JobConfigs
        raw_dict.setdefault("config_file_path", config_file_path)

        if packages := raw_dict.get("packages"):
            for package in packages.values():
                up_url_key = "upstream_project_url"
                if up_url_key in raw_dict:
                    # propagate it to any monorepo sub-package
                    package[up_url_key] = raw_dict[up_url_key]
                cls.set_defaults(
                    package,
                    repo_name,
                    search_specfile,
                    **specfile_search_args,
                )
        else:
            cls.set_defaults(
                raw_dict,
                repo_name,
                search_specfile,
                **specfile_search_args,
            )

        return cls.get_from_dict_without_setting_defaults(raw_dict)

    @classmethod
    def get_from_dict_without_setting_defaults(
        cls,
        raw_dict: dict,
    ) -> "PackageConfig":
        # required to avoid cyclical imports
        from packit.schema import PackageConfigSchema

        package_config = PackageConfigSchema().load(raw_dict)
        package_config._raw_dict_with_defaults = raw_dict
        return cls.post_load(package_config)

    def get_raw_dict_with_defaults(self):
        return self._raw_dict_with_defaults

    @classmethod
    def post_load(cls, package_config: "PackageConfig") -> "PackageConfig":
        if not package_config:
            return None

        package_config_views: dict[str, PackageConfigView] = {}
        for name, package in package_config.packages.items():
            # filter out job data for the package
            jobs = [
                job for job in package_config.get_job_views() if name in job.packages
            ]
            package_config_views[name] = PackageConfigView(
                packages={name: package},
                jobs=jobs,
            )
        package_config.set_package_config_views(package_config_views)

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
                f" if this is not the one you want.",
            )
        return projects_list[0]

    def get_propose_downstream_dg_branches_value(
        self,
        pull_from_upstream=False,
    ) -> Optional[list]:
        type = (
            JobType.pull_from_upstream
            if pull_from_upstream
            else JobType.propose_downstream
        )
        for job in self.jobs:
            if job.type == type:
                return job.dist_git_branches
        return []

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

    def get_job_views(self) -> list[Union[JobConfig, JobConfigView]]:
        """Get jobs views on a single package.
        If a JobConfig reference more than a package, then
        split it in many JobConfigView(s) one for any package
        """
        if self._job_views:
            return self._job_views

        for job in self.jobs:
            if len(self.packages) > 1:
                for name in job.packages:
                    job_view = JobConfigView(job, name)
                    self._job_views.append(job_view)
            else:
                self._job_views.append(job)
        return self._job_views

    def get_package_config_views(self) -> dict[str, "PackageConfigView"]:
        """Return a dictionary of package name -> PackageConfigView
        every PackageConfigView holds just one package (the named one)
        and its associated jobs.
        A Monorepo PackageConfig will be splitted in many of them.

        NOTE: not using a property because of the custom __getattr__
        """
        return self._package_config_views

    def set_package_config_views(self, value: dict[str, "PackageConfigView"]):
        """Set a dictionary of package name -> PackageConfigView
        every PackageConfigView holds just one package (the named one)
        and its associated jobs.
        A Monorepo PackageConfig will be split in many of them.

        NOTE: not using a property because of the custom __setattr__
        """
        self._package_config_views = value

    def get_package_config_for(
        self,
        job_config: Union[JobConfigView, JobConfig],
    ) -> Union["PackageConfigView", "PackageConfig"]:
        """Select the PackageConfigView for the given JobConfig in
        a multiple packages config.
        """
        package_config_views = self.get_package_config_views()
        if not package_config_views or not job_config:
            # the package config views were not initialized
            # we can continue if this is not a monorepo
            if len(self.packages) == 1:
                return self
        else:
            if not isinstance(job_config, JobConfigView):
                # the job config should have just one package,
                # choose that one
                return package_config_views[next(iter(job_config.packages.keys()))]

        return package_config_views[job_config.package]


class PackageConfigView(PackageConfig):
    """A PackageConfig which holds:
    - one single package config (no more than one CommonPackageConfig object)
    - only jobs related with the given package config

    The PackageConfig is responsible to build this object
    filtering out all the data related to a single package
    """

    def __init__(
        self,
        packages: dict[str, CommonPackageConfig],
        jobs: Optional[list[JobConfig]] = None,
    ):
        if len(packages) > 1:
            logger.error(
                "The PackageConfigView class deals with just one single package",
            )
        super().__init__(packages, jobs)


def find_packit_yaml(
    *directory: Union[Path, str],
    try_local_dir_first: bool = False,
    try_local_dir_last: bool = False,
) -> Path:
    """
    Find packit config in provided directories.

    Args:
        directory: List of directories where we should look for the config.
        try_local_dir_first: If set to `True` check the current working directory
            first.

            Defaults to `False`.
        try_local_dir_last: If set to `True` check the current working directory
            last.

            Defaults to `False`.

    Returns:
        Path to the config.

    Raises:
        PackitConfigException: If no config is found.
    """
    directories = [Path(config_dir) for config_dir in directory]
    cwd = Path.cwd()

    if try_local_dir_first and try_local_dir_last:
        logger.error(
            "Ambiguous usage of 'try_local_dir_first' and 'try_local_dir_last'.",
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
    config_file_path: Optional[Path] = None,
    raw_text: str = "",
) -> dict:
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
        config = safe_load(raw_text) or {}
        # Ignore yaml anchor placeholders
        config.pop("_", None)
        return config
    except YAMLError as ex:
        logger.error(f"Cannot load package config {config_file_path}.")
        if hasattr(ex, "problem_mark"):
            msg = (
                "  parser says\n"
                + str(ex.problem_mark)
                + "\n  "
                + str(ex.problem)  # type: ignore
            )  # type: ignore
            if ex.context is not None:  # type: ignore
                msg += f" {ex.context!s}"  # type: ignore
            logger.error(msg)
        else:
            logger.error(f"parser says: {ex!r}.")
        raise PackitConfigException("Please correct data and retry.") from ex


def get_local_package_config(
    *directory: Union[Path, str],
    repo_name: Optional[str] = None,
    try_local_dir_first: bool = False,
    try_local_dir_last: bool = False,
    package_config_path: Optional[Union[Path, str]] = None,
) -> PackageConfig:
    """
    Finds and loads packit config from the provided directories.

    Args:
        directory: List of directories to look for packit config in.
        repo_name: Name of the git repository (default for project name).
        try_local_dir_first: If set to `True` check the current working directory
            first.

            Defaults to `False`.
        try_local_dir_last: If set to `True` check the current working directory
            last.

            Defautls to `False`.
        package_config_path: Path to the package configuration file.

    Returns:
        Loaded config as a `PackageConfig`.
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


def find_remote_package_config(
    project: GitProject,
    ref: Optional[str] = None,
) -> Optional[str]:
    """
    Check if there's a package config file
    in the given project (top-level directory only).

    Args:
        project: ogr Git-project object.
        ref: Optional ref at which the config should be searched for.

    Returns:
        Name of the found config file or None if there's no such file.
    """

    try:
        candidates = set(project.get_files(ref=ref, recursive=False))
    except GithubAppNotInstalledError:
        logger.warning(
            "The Packit GitHub App is not installed"
            f"for the {project.full_repo_name!r} repository.",
        )
        return None
    except APIException as ex:
        if ex.response_code == 404:
            # we couldn't find the project or git reference
            logger.warning(f"No project or ref was found: {ex}")
            return None
        raise

    try:
        package_config_name = (candidates & CONFIG_FILE_NAMES).pop()
    except KeyError:
        logger.warning(
            f"No config file ({CONFIG_FILE_NAMES}) found on ref {ref!r} "
            f"of the {project.full_repo_name!r} repository.",
        )
        return None

    logger.debug(
        f"Found a config file {package_config_name!r} "
        f"on ref {ref!r} "
        f"of the {project.full_repo_name!r} repository.",
    )
    return package_config_name


def get_package_config_from_repo(
    project: GitProject,
    ref: Optional[str] = None,
    package_config_path: Optional[str] = None,
) -> Optional[PackageConfig]:
    """Search for the package config in a remote repo, load it and return
    the package configuration object.

    Args:
        project: ogr Git-project object.
        ref: Optional ref at which the config should be searched for.
        package_config_path: path of the package config, relative to the repo root.
            Load and parse this when specified instead of searching for one.

    Returns:
        PackageConfig object constructed from the config file found in
        the repo or None if there's no package config in the repo.
    """
    if not (
        package_config_path := package_config_path
        or find_remote_package_config(project, ref)
    ):
        return None

    try:
        config_file_content = project.get_file_content(
            path=package_config_path,
            ref=ref,
        )
    except FileNotFoundError:
        logger.warning(
            f"No config file {package_config_path!r} found on ref {ref!r} "
            f"of the {project.full_repo_name!r} repository.",
        )
        return None
    loaded_config = load_packit_yaml(raw_text=config_file_content)

    return parse_loaded_config(
        loaded_config=loaded_config,
        config_file_path=package_config_path,
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
        f"Package config before loading:\n{json.dumps(loaded_config, indent=4)}",
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
        raise PackitConfigException(f"Cannot parse package config. {ex!r}") from ex


def get_local_specfile_path(
    dir: Path,
    exclude: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Get the path to the local specfile if present. If specfile is not found in
    the directory itself, search for it recursively (rglob).

    Args:
        dir: Directory to find the specfile in.
        exclude: Directories to be excluded from the recursive search.

            Defaults to `["tests"]`.

    Returns:
        Path (relative to the `dir`) of the specfile that was found first.
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


def get_specfile_path_from_repo(
    project: GitProject,
    ref: Optional[str] = None,
) -> Optional[str]:
    """
    Get the path of the specfile in the given repo if present.

    Args:
        project: Repository to look for the specfile in.
        ref: Git reference where the specfile is to be found.

            Defaults to repository's default branch.

    Returns:
        Path to the specfile or `None` if not found.
    """
    spec_files = project.get_files(ref=ref, filter_regex=r".+\.spec$")

    if not spec_files:
        logger.debug(f"No spec file found in {project.full_repo_name!r}")
        return None
    return spec_files[0]
