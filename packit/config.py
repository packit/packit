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

import json
import logging
import os
import warnings
from enum import Enum
from functools import lru_cache, partial
from pathlib import Path
from pprint import pformat
from typing import Optional, List, Dict, Set, Union

import click
from jsonschema import Draft4Validator, ValidationError
from lazy_object_proxy import Proxy
from yaml import safe_load

from ogr import GithubService, get_instances_from_dict, PagureService, get_project
from ogr.abstract import GitProject, GitService
from ogr.exceptions import OgrException
from packit.actions import ActionName
from packit.constants import CONFIG_FILE_NAMES, PROD_DISTGIT_URL, SANDCASTLE_WORK_DIR
from packit.exceptions import (
    PackitConfigException,
    PackitException,
    PackitInvalidConfigException,
)
from packit.schema import (
    USER_CONFIG_SCHEMA,
    JOB_CONFIG_SCHEMA,
    PACKAGE_CONFIG_SCHEMA,
    SYNCED_FILES_SCHEMA,
)
from packit.sync import RawSyncFilesItem, SyncFilesItem, get_raw_files
from packit.utils import nested_get

logger = logging.getLogger(__name__)


class BaseConfig:
    """ common ancestor for all the config classes, the boring stuff """

    SCHEMA: dict

    @classmethod
    def validate(cls, raw_dict: dict) -> None:
        try:
            Draft4Validator(cls.SCHEMA).validate(raw_dict)
        except ValidationError as ex:
            logger.debug(f"{pformat(raw_dict)}")
            raise PackitInvalidConfigException(
                f"Provided configuration is not valid: {ex}."
            )


class Config(BaseConfig):
    SCHEMA = USER_CONFIG_SCHEMA

    def __init__(self):
        self.debug: bool = False
        self.fas_user: Optional[str] = None
        self.keytab_path: Optional[str] = None

        self.webhook_secret: str = ""
        self.dry_run: bool = False

        self.services: Set[GitService] = set()

        # %%% ACTIONS HANDLER CONFIGURATION %%%
        # these values are specific to packit service when we run actions in a sandbox
        # users will never set these, so let's hide those from them

        # name of the handler to run actions and commands, default to current env
        self.command_handler: RunCommandType = RunCommandType.local
        # a dir where the PV is mounted: both in sandbox and in worker
        self.command_handler_work_dir: str = ""
        # name of the PVC so that the sandbox has the same volume mounted
        self.command_handler_pvc_env_var: str = ""  # pointer to pointer, lol
        # name of sandbox container image
        self.command_handler_image_reference: str = "docker.io/usercont/sandcastle"
        # do I really need to explain this?
        self.command_handler_k8s_namespace: str = "myproject"

        # path to a file where OGR should store HTTP requests
        # this is used for packit testing: don't expose this to users
        self.github_requests_log_path: str = ""

    @classmethod
    def get_user_config(cls) -> "Config":
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            directory = Path(xdg_config_home)
        else:
            directory = Path.home() / ".config"

        logger.debug(f"Loading user config from directory: {directory}")

        loaded_config: dict = {}
        for config_file_name in CONFIG_FILE_NAMES:
            config_file_name_full = directory / config_file_name
            logger.debug(f"Trying to load user config from: {config_file_name_full}")
            if config_file_name_full.is_file():
                try:
                    loaded_config = safe_load(open(config_file_name_full))
                except Exception as ex:
                    logger.error(f"Cannot load user config '{config_file_name_full}'.")
                    raise PackitException(f"Cannot load user config: {ex}.")
                break
        return Config.get_from_dict(raw_dict=loaded_config)

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "Config":
        if validate:
            cls.validate(raw_dict)

        config = Config()

        config.debug = raw_dict.get("debug", False)
        config.dry_run = raw_dict.get("dry_run", False)
        config.fas_user = raw_dict.get("fas_user", None)
        config.keytab_path = raw_dict.get("keytab_path", None)

        config.webhook_secret = raw_dict.get("webhook_secret", "")

        config.command_handler = RunCommandType.local
        a_h = raw_dict.get("command_handler")
        if a_h:
            config.command_handler = RunCommandType(a_h)
        config.command_handler_work_dir = raw_dict.get(
            "command_handler_work_dir", SANDCASTLE_WORK_DIR
        )
        config.command_handler_pvc_env_var = raw_dict.get(
            "command_handler_pvc_env_var", "SANDCASTLE_PVC"
        )
        config.command_handler_image_reference = raw_dict.get(
            "command_handler_image_reference", "docker.io/usercont/sandcastle"
        )
        # default project for oc cluster up
        config.command_handler_k8s_namespace = raw_dict.get(
            "command_handler_k8s_namespace", "myproject"
        )

        config.services = Config.load_authentication(raw_dict)
        return config

    @staticmethod
    def load_authentication(raw_dict):
        services = set()
        if "authentication" in raw_dict:
            services = get_instances_from_dict(instances=raw_dict["authentication"])
        else:
            logger.warning(
                "Please, "
                "use 'authentication' key in the user configuration "
                "to set tokens for GitHub and Pagure. "
                "New method supports more services and direct keys will be removed in the future.\n"
                "Example:\n"
                "authentication:\n"
                "    github.com:\n"
                "        token: GITHUB_TOKEN\n"
                "    pagure:\n"
                "        token: PAGURE_TOKEN\n"
                '        instance_url: "https://src.fedoraproject.org"\n'
            )
            github_app_id = raw_dict.get("github_app_id")
            github_app_cert_path = raw_dict.get("github_app_cert_path")
            github_token = raw_dict.get("github_token")
            services.add(
                GithubService(
                    token=github_token,
                    github_app_id=github_app_id,
                    github_app_private_key_path=github_app_cert_path,
                )
            )
            pagure_user_token = raw_dict.get("pagure_user_token")
            if raw_dict.get("pagure_fork_token"):
                warnings.warn(
                    "packit no longer accepts 'pagure_fork_token'"
                    " value (https://github.com/packit-service/packit/issues/495)"
                )
            services.add(
                PagureService(
                    token=pagure_user_token,
                    instance_url="https://src.fedoraproject.org",
                )
            )

        return services

    def _get_project(self, url: str) -> GitProject:
        try:
            project = get_project(url=url, custom_instances=self.services)
        except OgrException as ex:
            msg = f"Authentication for url '{url}' is missing in the config."
            logger.warning(msg)
            raise PackitConfigException(msg, ex)
        return project

    def get_project(self, url: str) -> GitProject:
        return Proxy(partial(self._get_project, url))


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
        auto_envvar_prefix="PACKIT",
        default_map=get_default_map_from_file(),
    )


class RunCommandType(Enum):
    sandcastle = "sandcastle"
    local = "local"


class JobType(Enum):
    """ Type of the job to execute: pick the correct handler """

    propose_downstream = "propose_downstream"
    check_downstream = "check_downstream"
    build = "build"
    sync_from_downstream = "sync_from_downstream"
    copr_build = "copr_build"
    add_to_whitelist = "add_to_whitelist"
    tests = "tests"
    report_test_results = "report_test_results"
    pull_request_action = "pull_request_action"
    copr_build_finished = "copr_build_finished"
    copr_build_started = "copr_build_started"


class JobTriggerType(Enum):
    release = "release"
    pull_request = "pull_request"
    commit = "commit"
    installation = "installation"
    testing_farm_results = "testing_farm_results"
    comment = "comment"


class JobNotifyType(Enum):
    pull_request_status = "pull_request_status"

    @classmethod
    def from_list(cls, li: List[str]) -> List["JobNotifyType"]:
        return [cls[i] for i in li]


class JobConfig(BaseConfig):
    SCHEMA = JOB_CONFIG_SCHEMA

    def __init__(
        self,
        job: JobType,
        notify: List[JobNotifyType],
        trigger: JobTriggerType,
        metadata: dict,
    ):
        self.job = job
        self.notify = notify
        self.trigger = trigger
        self.metadata = metadata

    def __repr__(self):
        return (
            f"JobConfig(job={self.job}, notify={self.notify},"
            f" trigger={self.trigger}, meta={self.metadata})"
        )

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "JobConfig":
        if validate:
            cls.validate(raw_dict)

        return JobConfig(
            job=JobType[raw_dict["job"]],
            trigger=JobTriggerType[raw_dict["trigger"]],
            notify=JobNotifyType.from_list(raw_dict.get("notify", [])),
            metadata=raw_dict.get("metadata", {}),
        )

    def __eq__(self, other: object):
        if not isinstance(other, JobConfig):
            raise PackitConfigException("Provided object is not a JobConfig instance.")
        return (
            self.job == other.job
            and self.notify == other.notify
            and self.trigger == other.trigger
            and self.metadata == other.metadata
        )


class SyncFilesConfig(BaseConfig):
    SCHEMA = SYNCED_FILES_SCHEMA

    def __init__(self, files_to_sync: List[SyncFilesItem]):
        self.files_to_sync: List[SyncFilesItem] = files_to_sync

    def __repr__(self):
        return f"SyncFilesConfig({self.files_to_sync!r})"

    def get_raw_files_to_sync(
        self, src_dir: Path, dest_dir: Path
    ) -> List[RawSyncFilesItem]:
        """
        Evaluate sync_files: render globs and prepend full paths
        """
        raw_files_to_sync: List[RawSyncFilesItem] = []
        for sync in self.files_to_sync:
            raw_files_to_sync += get_raw_files(src_dir, dest_dir, sync)
        return raw_files_to_sync

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "SyncFilesConfig":
        if validate:
            cls.validate(raw_dict)

        files_to_sync = []
        if isinstance(raw_dict, list):
            for f in raw_dict:
                if isinstance(f, dict):
                    files_to_sync.append(SyncFilesItem(src=f["src"], dest=f["dest"]))
                else:
                    files_to_sync.append(SyncFilesItem(src=f, dest=f))
        if isinstance(raw_dict, dict):
            for f in raw_dict:
                files_to_sync.append(SyncFilesItem(src=f["src"], dest=f["dest"]))

        return SyncFilesConfig(files_to_sync=files_to_sync)

    def __eq__(self, other: object):
        if not isinstance(other, SyncFilesConfig):
            return NotImplemented

        if not self.files_to_sync and not other.files_to_sync:
            return True

        if len(self.files_to_sync) != len(other.files_to_sync):
            return False

        return self.files_to_sync == other.files_to_sync


class PackageConfig(BaseConfig):
    """
    Config class for upstream/downstream packages;
    this is the config people put in their repos
    """

    SCHEMA = PACKAGE_CONFIG_SCHEMA

    def __init__(
        self,
        specfile_path: Optional[str] = None,
        synced_files: Optional[SyncFilesConfig] = None,
        jobs: Optional[List[JobConfig]] = None,
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
        create_pr: bool = False,
        spec_source_id: str = "Source0",
        upstream_tag_template: str = "{version}",
    ):
        self.specfile_path: Optional[str] = specfile_path
        self.synced_files: SyncFilesConfig = synced_files or SyncFilesConfig([])
        self.jobs: List[JobConfig] = jobs or []
        self.dist_git_namespace: str = dist_git_namespace or "rpms"
        self.upstream_project_url: Optional[str] = upstream_project_url
        self.upstream_package_name: Optional[str] = upstream_package_name
        # this is generated by us
        self._downstream_package_name: Optional[str] = downstream_package_name
        self.dist_git_base_url: str = dist_git_base_url or PROD_DISTGIT_URL
        self._downstream_project_url: str = downstream_project_url
        # path to a local git clone of the dist-git repo; None means to clone in a tmpdir
        self.dist_git_clone_path: Optional[str] = None
        self.actions = actions or {}
        self.upstream_ref: Optional[str] = upstream_ref
        self.allowed_gpg_keys = allowed_gpg_keys
        self.create_pr: bool = create_pr
        self.spec_source_id: str = spec_source_id

        # command to generate a tarball from the upstream repo
        # uncommitted changes will not be present in the archive
        self.create_tarball_command: List[str] = create_tarball_command
        # command to get current version of the project
        self.current_version_command: List[str] = current_version_command or [
            "git",
            "describe",
            "--tags",
            "--match",
            "*",
        ]
        # template to create an upstream tag name (upstream may use different tagging scheme)
        self.upstream_tag_template = upstream_tag_template

    @property
    def downstream_package_name(self) -> str:
        if not self._downstream_package_name:
            raise PackitConfigException("downstream_package_name is not set")
        return self._downstream_package_name

    @property
    def downstream_project_url(self) -> str:
        if not self._downstream_project_url:
            self._downstream_project_url = self.dist_git_package_url
        return self._downstream_project_url

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            return NotImplemented
        logger.debug(f"our configuration:\n{self.__dict__}")
        logger.debug(f"the other configuration:\n{other.__dict__}")
        return (
            self.specfile_path == other.specfile_path
            and self.synced_files == other.synced_files
            and self.jobs == other.jobs
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

    @property
    def dist_git_package_url(self):
        return (
            f"{self.dist_git_base_url}{self.dist_git_namespace}/"
            f"{self.downstream_package_name}.git"
        )

    @classmethod
    def get_from_dict(cls, raw_dict: dict, validate=True) -> "PackageConfig":
        if validate:
            cls.validate(raw_dict)

        synced_files = raw_dict.get("synced_files", None)
        actions = raw_dict.get("actions", {})
        raw_jobs = raw_dict.get("jobs", [])
        create_tarball_command = raw_dict.get("create_tarball_command", None)
        current_version_command = raw_dict.get("current_version_command", None)

        upstream_package_name = cls.get_deprecated_key(
            raw_dict, "upstream_package_name", "upstream_project_name"
        ) or cls.get_deprecated_key(raw_dict, "upstream_package_name", "upstream_name")
        upstream_project_url = raw_dict.get("upstream_project_url", None)

        if raw_dict.get("dist_git_url", None):
            logger.warning(
                "dist_git_url is no longer being processed, "
                "it is generated from dist_git_base_url and downstream_package_name"
            )
        downstream_package_name = cls.get_deprecated_key(
            raw_dict, "downstream_package_name", "package_name"
        )
        specfile_path = raw_dict.get("specfile_path", None)
        if not specfile_path:
            if downstream_package_name:
                specfile_path = f"{downstream_package_name}.spec"
                logger.info(f"We guess that spec file is at {specfile_path}")
            else:
                # guess it?
                logger.warning("Path to spec file is not set.")

        dist_git_base_url = raw_dict.get("dist_git_base_url", None)
        dist_git_namespace = raw_dict.get("dist_git_namespace", None)
        upstream_ref = nested_get(raw_dict, "upstream_ref")

        allowed_gpg_keys = raw_dict.get("allowed_gpg_keys", None)
        create_pr = raw_dict.get("create_pr", False)
        upstream_tag_template = raw_dict.get("upstream_tag_template", "{version}")

        # it can be int as well
        spec_source_id = raw_dict.get("spec_source_id", "Source0")
        try:
            spec_source_id = int(spec_source_id)
        except ValueError:
            # not a number
            pass
        else:
            # is a number!
            spec_source_id = f"Source{spec_source_id}"

        pc = PackageConfig(
            specfile_path=specfile_path,
            synced_files=SyncFilesConfig.get_from_dict(synced_files, validate=False),
            actions={ActionName(a): cmd for a, cmd in actions.items()},
            jobs=[
                JobConfig.get_from_dict(raw_job, validate=False) for raw_job in raw_jobs
            ],
            upstream_package_name=upstream_package_name,
            downstream_package_name=downstream_package_name,
            upstream_project_url=upstream_project_url,
            dist_git_base_url=dist_git_base_url,
            dist_git_namespace=dist_git_namespace,
            create_tarball_command=create_tarball_command,
            current_version_command=current_version_command,
            upstream_ref=upstream_ref,
            allowed_gpg_keys=allowed_gpg_keys,
            create_pr=create_pr,
            spec_source_id=spec_source_id,
            upstream_tag_template=upstream_tag_template,
        )
        return pc

    @staticmethod
    def get_deprecated_key(raw_dict: dict, new_key_name: str, old_key_name: str):
        old = raw_dict.get(old_key_name, None)
        if old:
            logger.warning(
                f"{old_key_name!r} configuration key was renamed to {new_key_name!r},"
                f" please update your configuration file"
            )
        r = raw_dict.get(new_key_name, None)
        if not r:
            # prio: new > old
            r = old
        return r


def get_local_package_config(
    *directory, try_local_dir_first=False, try_local_dir_last=False
) -> PackageConfig:
    """
    :return: local PackageConfig if present
    """
    directories = [Path(config_dir) for config_dir in directory]

    if try_local_dir_first:
        directories.insert(0, Path.cwd())

    if try_local_dir_last:
        directories.append(Path.cwd())

    for config_dir in directories:
        for config_file_name in CONFIG_FILE_NAMES:
            config_file_name_full = config_dir / config_file_name
            if config_file_name_full.is_file():
                logger.debug(f"Local package config found: {config_file_name_full}")
                try:
                    loaded_config = safe_load(open(config_file_name_full))
                except Exception as ex:
                    logger.error(
                        f"Cannot load package config '{config_file_name_full}'."
                    )
                    raise Exception(f"Cannot load package config: {ex}.")

                return parse_loaded_config(loaded_config=loaded_config)

            logger.debug(f"The local config file '{config_file_name_full}' not found.")
    raise PackitConfigException("No packit config found.")


def get_package_config_from_repo(
    sourcegit_project: GitProject, ref: str
) -> Optional[PackageConfig]:
    for config_file_name in CONFIG_FILE_NAMES:
        try:
            config_file_content = sourcegit_project.get_file_content(
                path=config_file_name, ref=ref
            )
            logger.debug(
                f"Found a config file '{config_file_name}' "
                f"on ref '{ref}' "
                f"of the {sourcegit_project.full_repo_name} repository."
            )
        except FileNotFoundError as ex:
            logger.debug(
                f"The config file '{config_file_name}' "
                f"not found on ref '{ref}' "
                f"of the {sourcegit_project.full_repo_name} repository."
                f"{ex!r}"
            )
            continue

        try:
            loaded_config = safe_load(config_file_content)
        except Exception as ex:
            logger.error(f"Cannot load package config '{config_file_name}'.")
            raise PackitException(f"Cannot load package config: {ex}.")

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
