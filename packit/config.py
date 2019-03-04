import json
import logging
from enum import IntEnum
from functools import lru_cache
from os import getenv, environ
from pathlib import Path
from typing import Optional, List, NamedTuple

import anymarkup
import click
import jsonschema
from jsonschema import Draft4Validator

from ogr.abstract import GitProject
from packit.constants import CONFIG_FILE_NAMES
from packit.exceptions import PackitConfigException
from packit.utils import exclude_from_dict

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self.debug = False
        self.fas_user = None
        self.keytab_path = None
        self._package_config = None
        self._github_token = None
        self._pagure_user_token = None
        self._pagure_package_token = None
        self._pagure_fork_token = None

    @property
    def github_token(self) -> str:
        if self._github_token is None:
            self._github_token = environ["GITHUB_TOKEN"]
        return self._github_token

    @property
    def pagure_user_token(self) -> str:
        if self._pagure_user_token is None:
            self._pagure_user_token = getenv("PAGURE_USER_TOKEN", "")
        return self._pagure_user_token

    @property
    def pagure_package_token(self) -> str:
        """ this token is used to comment on pull requests """
        if self._pagure_package_token is None:
            self._pagure_package_token = getenv("PAGURE_PACKAGE_TOKEN", "")
        return self._pagure_package_token

    @property
    def pagure_fork_token(self) -> str:
        """ this is needed to create pull requests """
        if self._pagure_fork_token is None:
            self._pagure_fork_token = getenv("PAGURE_FORK_TOKEN", "")
        return self._pagure_fork_token


pass_config = click.make_pass_decorator(Config)


def get_default_map_from_file() -> Optional[dict]:
    config_path = Path(".packit")
    if config_path.is_file():
        return json.loads(config_path.read_text())
    return None


@lru_cache()
def get_context_settings() -> dict:
    return dict(
        help_option_names=["-h", "--help"],
        auto_envvar_prefix="SOURCE_GIT",
        default_map=get_default_map_from_file(),
    )


class TriggerType(IntEnum):
    release = 1
    pull_request = 2
    git_tag = 3


class JobConfig(NamedTuple):
    trigger: TriggerType
    release_to: List[str]
    metadata: dict

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "JobConfig":
        if validate and not JobConfig.is_dict_valid(raw_dict):
            raise Exception(f"Job config not valid.")

        trigger_raw, release_to, metadata = exclude_from_dict(
            raw_dict, "trigger", "release_to"
        )
        return JobConfig(
            trigger=TriggerType[trigger_raw], release_to=release_to, metadata=metadata
        )

    @classmethod
    def is_dict_valid(cls, raw_dict: dict) -> bool:
        return Draft4Validator(JOB_CONFIG_SCHEMA).is_valid(raw_dict)


class PackageConfig:
    def __init__(
        self,
        specfile_path: Optional[str] = None,
        synced_files: Optional[List[str]] = None,
        jobs: Optional[List[JobConfig]] = None,
        metadata: Optional[dict] = None,
        dist_git_namespace: str = "rpms",
        upstream_project_url: str = ".",  # can be URL or path
    ):
        self.specfile_path: Optional[str] = specfile_path
        self.synced_files: Optional[List[str]] = synced_files
        self.jobs: Optional[List[JobConfig]] = jobs
        # TODO: the metadata should have a proper definition and validation
        self.metadata: Optional[dict] = metadata
        self.dist_git_namespace: str = dist_git_namespace
        self.upstream_project_url: str = upstream_project_url

    def __eq__(self, other: "PackageConfig"):
        return (
            self.specfile_path == other.specfile_path
            and self.synced_files == other.synced_files
            and self.jobs == other.jobs
            and self.metadata == other.metadata
            and self.dist_git_namespace == other.dist_git_namespace
            and self.upstream_project_url == other.upstream_project_url
        )

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "PackageConfig":
        if validate:
            PackageConfig.validate_dict(raw_dict)

        specfile_path, synced_files, raw_jobs, metadata = exclude_from_dict(
            raw_dict, "specfile_path", "synced_files", "jobs"
        )

        raw_jobs = raw_jobs or []

        pc = PackageConfig(
            specfile_path=specfile_path,
            synced_files=synced_files,
            jobs=[
                JobConfig.get_from_dict(raw_job, validate=False) for raw_job in raw_jobs
            ],
            metadata=metadata,
        )

        return pc

    @classmethod
    def validate_dict(cls, raw_dict: dict) -> None:
        jsonschema.validate(raw_dict, PACKAGE_CONFIG_SCHEMA)


def get_local_package_config(directory=None) -> PackageConfig:
    """
    :return: local PackageConfig if present
    """
    directory = Path(directory) or Path.cwd()
    for config_file_name in CONFIG_FILE_NAMES:
        config_file_name_full = directory / config_file_name
        if config_file_name_full.is_file():
            logger.debug(f"Local package config found: {config_file_name_full}")
            try:
                loaded_config = anymarkup.parse_file(config_file_name_full)
            except Exception as ex:
                logger.error(f"Cannot load package config '{config_file_name_full}'.")
                raise Exception(f"Cannot load package config: {ex}.")

            return parse_loaded_config(loaded_config=loaded_config)

        logger.debug(f"The local config file '{config_file_name_full}' not found.")
    raise PackitConfigException("No packit config found.")


def get_packit_config_from_repo(
    sourcegit_project: GitProject, ref: str
) -> Optional[PackageConfig]:
    for config_file_name in CONFIG_FILE_NAMES:
        try:
            config_file = sourcegit_project.get_file_content(
                path=config_file_name, ref=ref
            )
            logger.debug(
                f"Found a config file '{config_file_name}' "
                f"on ref '{ref}' "
                f"of the {sourcegit_project.full_repo_name} repository."
            )
        except FileNotFoundError:
            logger.debug(
                f"The config file '{config_file_name}' "
                f"not found on ref '{ref}' "
                f"of the {sourcegit_project.full_repo_name} repository."
            )
            continue

        try:
            loaded_config = anymarkup.parse(config_file)
        except Exception as ex:
            logger.error(f"Cannot load package config '{config_file_name}'.")
            raise Exception(f"Cannot load package config: {ex}.")

        return parse_loaded_config(loaded_config=loaded_config)

    return None


def parse_loaded_config(loaded_config: dict) -> PackageConfig:
    """Tries to parse the config to PackageConfig."""
    logger.debug(f"Package config:\n{json.dumps(loaded_config, indent=4)}")

    try:
        package_config = PackageConfig.get_from_dict(
            raw_dict=loaded_config, validate=True
        )
        return package_config
    except Exception as ex:
        logger.error(f"Cannot parse package config. {ex}.")
        raise Exception(f"Cannot parse package config: {ex}.")


JOB_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "trigger": {"enum": ["release", "pull_request", "git_tag"]},
        "release_to": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["trigger", "release_to"],
}

PACKAGE_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "specfile_path": {"type": "string"},
        "synced_files": {"type": "array", "items": {"type": "string"}},
        "jobs": {"type": "array", "items": JOB_CONFIG_SCHEMA},
    },
    "required": ["specfile_path", "synced_files"],
}
