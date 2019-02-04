from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Optional, List, Dict

import click
from jsonschema import Draft4Validator

from sourcegit.utils import exclude_from_dict


@dataclass
class Config:
    verbose: bool
    debug: bool
    fas_user: str
    keytab: str


pass_config = click.make_pass_decorator(Config)


def get_default_map_from_file() -> Optional[dict]:
    config_path = ".sourcegit"
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
    branch_commit = 3


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
    hooks: Optional[Dict[str, str]]  # action_name: script
    metadata: dict

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> PackageConfig:
        if validate and not PackageConfig.is_dict_valid(raw_dict):
            raise Exception("Package config not valid.")

        specfile_path, synced_files, raw_jobs, hooks, metadata = exclude_from_dict(
            raw_dict, "specfile_path", "synced_files", "jobs", "hooks"
        )

        return PackageConfig(
            specfile_path=specfile_path,
            synced_files=synced_files,
            jobs=[
                JobConfig.get_from_dict(raw_job, validate=False) for raw_job in raw_jobs
            ],
            hooks=hooks,
            metadata=metadata,
        )

    @classmethod
    def is_dict_valid(cls, raw_dict: dict) -> bool:
        return Draft4Validator(PACKAGE_CONFIG_SCHEMA).is_valid(raw_dict)


JOB_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "trigger": {"enum": ["release", "pull_request", "branch_commit"]},
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
        "hooks": {"type": "object", "items": {"type": "string"}},
    },
    "required": ["specfile_path", "synced_files", "jobs"],
}
