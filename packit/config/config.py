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
from typing import Optional, Set

import click
from lazy_object_proxy import Proxy
from yaml import safe_load

from ogr import GithubService, get_instances_from_dict, PagureService, get_project
from ogr.abstract import GitProject, GitService
from ogr.exceptions import OgrException
from packit.constants import CONFIG_FILE_NAMES, SANDCASTLE_WORK_DIR
from packit.config.base_config import BaseConfig
from packit.exceptions import PackitConfigException, PackitException
from packit.schema import USER_CONFIG_SCHEMA

logger = logging.getLogger(__name__)


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
