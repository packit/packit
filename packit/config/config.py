# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
import os
import warnings
from enum import Enum
from functools import lru_cache, partial
from pathlib import Path
from shutil import which
from typing import Optional

import click
from lazy_object_proxy import Proxy
from ogr import GithubService, PagureService, get_instances_from_dict, get_project
from ogr.abstract import GitProject, GitService
from ogr.exceptions import OgrException
from yaml import safe_load

from packit.constants import (
    CONFIG_FILE_NAMES,
    SANDCASTLE_DEFAULT_PROJECT,
    SANDCASTLE_IMAGE,
    SANDCASTLE_PVC,
    SANDCASTLE_WORK_DIR,
)
from packit.exceptions import PackitConfigException, PackitException

logger = logging.getLogger(__name__)


class Config:
    def __init__(
        self,
        debug: bool = False,
        fas_user: Optional[str] = None,
        fas_password: Optional[str] = None,
        keytab_path: Optional[str] = None,
        redhat_api_refresh_token: Optional[str] = None,
        upstream_git_remote: Optional[str] = None,
        kerberos_realm: Optional[str] = "FEDORAPROJECT.ORG",
        koji_build_command: Optional[str] = "koji build",
        pkg_tool: str = "fedpkg",
        command_handler: Optional[str] = None,
        command_handler_work_dir: str = SANDCASTLE_WORK_DIR,
        command_handler_pvc_env_var: str = SANDCASTLE_PVC,
        command_handler_image_reference: str = SANDCASTLE_IMAGE,
        command_handler_k8s_namespace: str = SANDCASTLE_DEFAULT_PROJECT,
        command_handler_pvc_volume_specs: Optional[list[dict[str, str]]] = None,
        command_handler_storage_class: str = "",
        appcode: str = "",
        package_config_path=None,
        repository_cache=None,
        add_repositories_to_repository_cache=True,
        default_parse_time_macros: Optional[dict] = None,
        **kwargs,
    ):
        self.debug: bool = debug
        self.fas_user: Optional[str] = fas_user
        self.fas_password: Optional[str] = fas_password
        self.keytab_path: Optional[str] = keytab_path
        self.redhat_api_refresh_token: Optional[str] = redhat_api_refresh_token
        self.kerberos_realm = kerberos_realm
        self.koji_build_command = koji_build_command
        if not which(pkg_tool):
            logger.warning(f"{pkg_tool} is not executable or in any path")
        self.pkg_tool: str = pkg_tool
        self.upstream_git_remote = upstream_git_remote

        self.services: set[GitService] = set()

        # %%% ACTIONS HANDLER CONFIGURATION %%%
        # these values are specific to packit service when we run actions in a sandbox
        # users will never set these, so let's hide those from them

        # name of the handler to run actions and commands, default to current env
        self.command_handler: RunCommandType = (
            RunCommandType(command_handler) if command_handler else RunCommandType.local
        )
        # a dir where the PV is mounted: both in sandbox and in worker
        self.command_handler_work_dir: str = command_handler_work_dir
        # name of the PVC so that the sandbox has the same volume mounted
        self.command_handler_pvc_env_var: str = (
            command_handler_pvc_env_var  # pointer to pointer
        )
        # name of sandbox container image
        self.command_handler_image_reference: str = command_handler_image_reference
        # do I really need to explain this?
        self.command_handler_k8s_namespace: str = command_handler_k8s_namespace
        # To be able to mount other volumes (like repository cache) to the sandcastle pod.
        # The keys are not checked by marshmallow to support any argument supported by Sandcastle.
        # e.g. you can set `path` and `pvc`/`pvc_from_env`
        self.command_handler_pvc_volume_specs: list[dict[str, str]] = (
            command_handler_pvc_volume_specs or []
        )
        # To specify PVCs' storage class (differes in auto-prod and MP+)
        self.command_handler_storage_class = command_handler_storage_class

        # Needs to be used for requesting PVCs in Sandcastle
        self.appcode = appcode

        # path to a file where OGR should store HTTP requests
        # this is used for packit testing: don't expose this to users
        self.github_requests_log_path: str = ""

        self.services = Config.load_authentication(kwargs)
        self.package_config_path = package_config_path
        self.repository_cache = repository_cache
        self.add_repositories_to_repository_cache = add_repositories_to_repository_cache
        self.default_parse_time_macros = default_parse_time_macros or {}

        # because of current load_authentication implementation it will generate false warnings
        # if kwargs:
        #     logger.warning(f"Following kwargs were not processed:" f"{kwargs}")

    def __repr__(self):
        return (
            "Config("
            f"debug='{self.debug}', "
            f"fas_user='{self.fas_user}', "
            f"keytab_path='{self.keytab_path}', "
            f"kerberos_realm='{self.kerberos_realm}', "
            f"koji_build_command='{self.koji_build_command}', "
            f"pkg_tool='{self.pkg_tool}', "
            f"upstream_git_remote='{self.upstream_git_remote}', "
            f"command_handler='{self.command_handler}', "
            f"command_handler_work_dir='{self.command_handler_work_dir}', "
            f"command_handler_pvc_env_var='{self.command_handler_pvc_env_var}', "
            f"command_handler_image_reference='{self.command_handler_image_reference}', "
            f"command_handler_k8s_namespace='{self.command_handler_k8s_namespace}', "
            f"command_handler_pvc_volume_specs='{self.command_handler_pvc_volume_specs}', "
            f"command_handler_storage_class='{self.command_handler_storage_class}', "
            f"appcode='{self.appcode}', "
            f"repository_cache='{self.repository_cache}', "
            f"default_parse_time_macros='{self.default_parse_time_macros}')"
        )

    @classmethod
    def get_user_config(cls) -> "Config":
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        directory = (
            Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
        )

        logger.debug(f"Loading user config from directory: {directory}")

        loaded_config: dict = {}
        for config_file_name in CONFIG_FILE_NAMES:
            config_file_name_full = directory / config_file_name
            logger.debug(f"Trying to load user config from: {config_file_name_full}")
            if config_file_name_full.is_file():
                try:
                    with open(config_file_name_full) as file:
                        loaded_config = safe_load(file)
                except Exception as ex:
                    logger.error(f"Cannot load user config {config_file_name_full!r}.")
                    raise PackitException(f"Cannot load user config: {ex!r}.") from ex
                break
        return Config.get_from_dict(raw_dict=loaded_config)

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "Config":
        # required to avoid cyclical imports
        from packit.schema import UserConfigSchema

        config = UserConfigSchema().load(raw_dict)
        logger.debug(f"Loaded config: {config}")

        return config

    @staticmethod
    def load_authentication(raw_dict):
        services = set()
        deprecated_keys = [
            "github_app_id",
            "github_app_cert_path",
            "github_token",
            "pagure_user_token",
            "pagure_instance_url",
            "pagure_fork_token",
        ]
        if "authentication" in raw_dict:
            services = get_instances_from_dict(instances=raw_dict["authentication"])
        elif any(key in raw_dict for key in deprecated_keys):
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
                "See our documentation for more information "
                "http://packit.dev/docs/configuration/#user-configuration-file. ",
            )
            github_app_id = raw_dict.get("github_app_id")
            github_app_cert_path = raw_dict.get("github_app_cert_path")
            github_token = raw_dict.get("github_token")
            services.add(
                GithubService(
                    token=github_token,
                    github_app_id=github_app_id,
                    github_app_private_key_path=github_app_cert_path,
                ),
            )
            pagure_user_token = raw_dict.get("pagure_user_token")
            pagure_instance_url = raw_dict.get(
                "pagure_instance_url",
                "https://src.fedoraproject.org",
            )
            if raw_dict.get("pagure_fork_token"):
                warnings.warn(
                    "packit no longer accepts 'pagure_fork_token'"
                    " value (https://github.com/packit/packit/issues/495)",
                    stacklevel=2,
                )
            services.add(
                PagureService(
                    token=pagure_user_token,
                    instance_url=pagure_instance_url,
                ),
            )

        return services

    def _get_project(
        self,
        url: str,
        required: bool = True,
        get_project_kwargs: Optional[dict] = None,
    ) -> Optional[GitProject]:
        """
        Gets a GitProject for the given URL.

        Args:
            url: Project URL.
            required: Whether to raise an exception on failure or return None.
            get_project_kwargs: Keyword arguments to be passed to ogr's get_project().

        Returns:
            GitProject instance or None if the underlying get_project() call fails
            and required is False.

        Raises:
            PackitConfigException if the underlying get_project() call fails
            and required is True.
        """
        get_project_kwargs = get_project_kwargs or {}
        try:
            project = get_project(
                url=url,
                custom_instances=self.services,
                **get_project_kwargs,
            )
        except OgrException as ex:
            msg = f"Authentication for url {url!r} is missing in the config."
            logger.warning(msg)
            if required:
                raise PackitConfigException(msg) from ex
            return None
        return project

    def get_project(
        self,
        url: str,
        required: bool = True,
        get_project_kwargs: Optional[dict] = None,
    ) -> Proxy:
        """
        Gets a proxy of GitProject for the given URL. On access, if the underlying
        get_project() call fails, the behaviour depends on the `required` argument.
        If set to True (the default), a PackitConfigException is raised, otherwise
        the proxy acts as it was None.

        Args:
            url: Project URL.
            required: Whether to raise an exception on failure or act as None.
            get_project_kwargs: Keyword arguments to be passed to ogr's get_project().

        Returns:
            Proxy of a GitProject instance or None.
        """
        return Proxy(partial(self._get_project, url, required, get_project_kwargs))


pass_config = click.make_pass_decorator(Config)


def get_default_map_from_file() -> Optional[dict]:
    config_path = Path(".packit")
    if config_path.is_file():
        return json.loads(config_path.read_text())
    return None


@lru_cache
def get_context_settings() -> dict:
    return {
        "help_option_names": ["-h", "--help"],
        "auto_envvar_prefix": "PACKIT",
        "default_map": get_default_map_from_file(),
    }


class RunCommandType(Enum):
    sandcastle = "sandcastle"
    local = "local"
