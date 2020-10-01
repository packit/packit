# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
from typing import Optional, Set

import click
from lazy_object_proxy import Proxy
from yaml import safe_load

from ogr import GithubService, get_instances_from_dict, PagureService, get_project
from ogr.abstract import GitProject, GitService
from ogr.exceptions import OgrException
from packit.constants import (
    CONFIG_FILE_NAMES,
    SANDCASTLE_WORK_DIR,
    SANDCASTLE_PVC,
    SANDCASTLE_DEFAULT_PROJECT,
    SANDCASTLE_IMAGE,
)
from packit.exceptions import PackitConfigException, PackitException

logger = logging.getLogger(__name__)


class Config:
    def __init__(
        self,
        debug: bool = False,
        dry_run: bool = False,
        fas_user: Optional[str] = None,
        keytab_path: Optional[str] = None,
        upstream_git_remote: Optional[str] = None,
        kerberos_realm: Optional[str] = "FEDORAPROJECT.ORG",
        command_handler: str = None,
        command_handler_work_dir: str = SANDCASTLE_WORK_DIR,
        command_handler_pvc_env_var: str = SANDCASTLE_PVC,
        command_handler_image_reference: str = SANDCASTLE_IMAGE,
        command_handler_k8s_namespace: str = SANDCASTLE_DEFAULT_PROJECT,
        **kwargs,
    ):
        self.debug: bool = debug
        self.fas_user: Optional[str] = fas_user
        self.keytab_path: Optional[str] = keytab_path
        self.kerberos_realm = kerberos_realm
        self.dry_run: bool = dry_run
        self.upstream_git_remote = upstream_git_remote

        self.services: Set[GitService] = set()

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

        # path to a file where OGR should store HTTP requests
        # this is used for packit testing: don't expose this to users
        self.github_requests_log_path: str = ""

        self.services = Config.load_authentication(kwargs)

        # because of current load_authentication implementation it will generate false warnings
        # if kwargs:
        #     logger.warning(f"Following kwargs were not processed:" f"{kwargs}")

    def __repr__(self):
        return (
            "Config("
            f"debug='{self.debug}', "
            f"fas_user='{self.fas_user}', "
            f"keytab_path='{self.keytab_path}', "
            f"upstream_git_remote='{self.upstream_git_remote}', "
            f"command_handler='{self.command_handler}', "
            f"command_handler_work_dir='{self.command_handler_work_dir}', "
            f"command_handler_pvc_env_var='{self.command_handler_pvc_env_var}', "
            f"command_handler_image_reference='{self.command_handler_image_reference}', "
            f"command_handler_k8s_namespace='{self.command_handler_k8s_namespace}')"
        )

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
                    logger.error(f"Cannot load user config {config_file_name_full!r}.")
                    raise PackitException(f"Cannot load user config: {ex!r}.")
                break
        return Config.get_from_dict(raw_dict=loaded_config)

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "Config":
        # required to avoid cyclical imports
        from packit.schema import UserConfigSchema

        config = UserConfigSchema().load_config(raw_dict)
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
                "http://packit.dev/docs/configuration/#user-configuration-file. "
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
            pagure_instance_url = raw_dict.get(
                "pagure_instance_url", "https://src.fedoraproject.org"
            )
            if raw_dict.get("pagure_fork_token"):
                warnings.warn(
                    "packit no longer accepts 'pagure_fork_token'"
                    " value (https://github.com/packit/packit/issues/495)"
                )
            services.add(
                PagureService(token=pagure_user_token, instance_url=pagure_instance_url)
            )

        return services

    def _get_project(self, url: str, get_project_kwargs: dict = None) -> GitProject:
        get_project_kwargs = get_project_kwargs or {}
        try:
            project = get_project(
                url=url, custom_instances=self.services, **get_project_kwargs
            )
        except OgrException as ex:
            msg = f"Authentication for url {url!r} is missing in the config."
            logger.warning(msg)
            raise PackitConfigException(msg, ex)
        return project

    def get_project(self, url: str, get_project_kwargs: dict = None) -> GitProject:
        return Proxy(partial(self._get_project, url, get_project_kwargs))


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
