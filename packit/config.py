from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Optional, List

import anymarkup
import click
from jsonschema import Draft4Validator

from ogr.abstract import GitProject
from packit.constants import CONFIG_FILE_NAMES
from packit.utils import exclude_from_dict

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self.verbose = False
        self.debug = False
        self.fas_user = None
        self.keytab_path = None
        self._package_config = None
        self._github_token = None
        self._pagure_user_token = None
        self._pagure_package_token = None
        self._pagure_fork_token = None

    @property
    def package_config(self) -> PackageConfig:
        if self._package_config is None:
            self._package_config = get_local_package_config()
        return self._package_config

    @property
    def github_token(self) -> str:
        if self._github_token is None:
            self._github_token = os.environ["GITHUB_TOKEN"]
        return self._github_token

    @property
    def pagure_user_token(self) -> str:
        if self._pagure_user_token is None:
            self._pagure_user_token = os.environ["PAGURE_USER_TOKEN"]
        return self._pagure_user_token

    @property
    def pagure_package_token(self) -> str:
        """ this token is used to comment on pull requests """
        if self._pagure_package_token is None:
            self._pagure_package_token = os.environ["PAGURE_PACKAGE_TOKEN"]
        return self._pagure_package_token

    @property
    def pagure_fork_token(self) -> str:
        """ this is needed to create pull requests """
        if self._pagure_fork_token is None:
            self._pagure_fork_token = os.environ["PAGURE_FORK_TOKEN"]
        return self._pagure_fork_token


pass_config = click.make_pass_decorator(Config)


def get_default_map_from_file() -> Optional[dict]:
    config_path = ".packit"
    if os.path.isfile(config_path):
        with open(config_path) as config_data:
            return json.load(config_data)
    return None


@lru_cache()
def get_context_settings() -> dict:
    return dict(
        help_option_names=["-h", "--help"],
        auto_envvar_prefix="SOURCE_GIT",
        default_map=get_default_map_from_file(),
    )


class TriggerType(Enum):
    release = 1
    pull_request = 2
    git_tag = 3


@dataclass(unsafe_hash=True, frozen=True)
class JobConfig:
    trigger: TriggerType
    release_to: List[str]
    metadata: dict

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> JobConfig:
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


@dataclass(unsafe_hash=True, frozen=True)
class PackageConfig:
    specfile_path: str
    synced_files: List[str]
    jobs: List[JobConfig]
    metadata: dict

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> PackageConfig:
        if validate and not PackageConfig.is_dict_valid(raw_dict):
            raise Exception("Package config not valid.")

        specfile_path, synced_files, raw_jobs, metadata = exclude_from_dict(
            raw_dict, "specfile_path", "synced_files", "jobs"
        )

        return PackageConfig(
            specfile_path=specfile_path,
            synced_files=synced_files,
            jobs=[
                JobConfig.get_from_dict(raw_job, validate=False) for raw_job in raw_jobs
            ],
            metadata=metadata,
        )

    @classmethod
    def is_dict_valid(cls, raw_dict: dict) -> bool:
        return Draft4Validator(PACKAGE_CONFIG_SCHEMA).is_valid(raw_dict)


def get_local_package_config(directory=None) -> Optional[PackageConfig]:
    """
    :return: local PackageConfig if present
    """
    directory = directory or os.path.curdir
    for config_file_name in CONFIG_FILE_NAMES:
        config_file_name_full = os.path.join(directory, config_file_name)
        if os.path.isfile(config_file_name_full):
            logger.debug(f"Local package config found: {config_file_name_full}")
            try:
                loaded_config = anymarkup.parse_file(config_file_name_full)
            except Exception as ex:
                logger.error(f"Cannot load package config '{config_file_name_full}'.")
                raise Exception(f"Cannot load package config: {ex}.")

            return parse_loaded_config(loaded_config=loaded_config)

        logger.debug(f"The local config file '{config_file_name_full}' not found.")

    return None


def get_packit_config_from_repo(
        sourcegit_project: GitProject, branch: str
) -> Optional[PackageConfig]:
    for config_file_name in CONFIG_FILE_NAMES:
        try:
            config_file = sourcegit_project.get_file_content(
                path=config_file_name, ref=branch
            )
            logger.debug(
                f"Found a config file '{config_file_name}' "
                f"on branch '{branch}' "
                f"of the {sourcegit_project.full_repo_name} repository."
            )
        except FileNotFoundError:
            logger.debug(
                f"The config file '{config_file_name}' "
                f"not found on branch '{branch}' "
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
    "required": ["specfile_path", "synced_files", "jobs"],
}
