# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Generate initial configuration for packit
"""

import logging
import os
from pathlib import Path
from typing import Optional

import click
import yaml

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import (
    cover_packit_exception,
    get_existing_config,
    get_latest_precommit_hook_release,
    get_precommit_config,
    is_file_empty,
)
from packit.config import get_context_settings
from packit.config.config import pass_config
from packit.config.package_config import get_local_specfile_path
from packit.constants import (
    PACKIT_CONFIG_TEMPLATE,
    PRECOMMIT_CONFIG_TEMPLATE,
)
from packit.exceptions import PackitException
from packit.utils import is_git_repo

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Reset config to default if already exists.",
)
@click.option(
    "--without-precommit",
    default=False,
    is_flag=True,
    help="Skip adding packit-specific pre-commit configuration hook.",
)
@click.option(
    "--force-precommit",
    default=False,
    is_flag=True,
    help="Create pre-commit configuration file if missing.",
)
@pass_config
@cover_packit_exception
def init(config, path_or_url, force, without_precommit, force_precommit):
    """
    Create the initial Packit configuration in a repository and add
    a pre-commit hook to validate Packit configuration file

    See 'packit source-git init', if you want to initialize a repository
    as a source-git repo.
    """
    working_dir = path_or_url.working_dir
    skip_precommit = False

    if without_precommit and force_precommit:
        raise PackitException(
            "--without-precommit and --force-precommit are"
            " mutually exclusive flags.",
        )

    precommit_config_path = get_precommit_config(working_dir)

    if force_precommit and not precommit_config_path:
        precommit_config_path = working_dir / ".pre-commit-config.yaml"
        precommit_config_path.touch()
    elif not precommit_config_path or without_precommit:
        skip_precommit = True

    if not skip_precommit:
        init_precommit(working_dir, precommit_config_path)  # type: ignore

    config_path = get_existing_config(working_dir)
    if config_path:
        if not force:
            raise PackitException(
                f"Packit config {config_path} already exists."
                " If you want to regenerate it, use `packit init --force`",
            )
    else:
        # Use default name
        config_path = working_dir / ".packit.yaml"

    specfile_path = get_local_specfile_path(working_dir)
    template_data = {
        "upstream_package_name": path_or_url.repo_name,
        "downstream_package_name": path_or_url.repo_name,
        "specfile_path": (
            specfile_path
            if specfile_path is not None
            else f"{path_or_url.repo_name}.spec"
        ),
    }

    with open(working_dir / ".gitignore", mode="a") as gitignore:
        print("prepare_sources_result*/", file=gitignore)

    generate_config(
        config_file=config_path,
        write_to_file=True,
        template_data=template_data,
    )


def generate_config(
    config_file: Path,
    write_to_file: bool = False,
    template_data: Optional[dict] = None,
) -> str:
    """
    Generate config file from provided data
    :param config_file: Path, .packit.yaml by default
    :param write_to_file: bool, write to config_file? False by default
    :param template_data: dict, example:
    {
        "upstream_package_name": "packitos",
        "downstream_package_name": "packit",
        "specfile_path": packit.spec,
    }
    :return: str, generated config
    """
    output_config = PACKIT_CONFIG_TEMPLATE.format(
        downstream_package_name=template_data["downstream_package_name"],
        upstream_package_name=template_data["upstream_package_name"],
        specfile_path=template_data["specfile_path"],
    )

    if write_to_file:
        config_file.write_text(output_config)
        logger.debug(f"Packit config file '{config_file}' changed.")

    return output_config


def init_precommit(
    working_dir: Path,
    precommit_config_path: Path,
):
    """
    Check that repo is initialized as a git repo and that a pre-commit
    configuration file is present before adding packit-specific
    pre-commit hook to it
    """
    if not is_git_repo(working_dir):
        raise PackitException(
            ".git repository not found."
            " Initialize current repository as a git repo first in order"
            " to set up Packit config validation upon pre-commit."
            " If you want do not want to use pre-commit for this purpose,"
            " re-run `packit init` using `--without-precommit` flag.",
        )

    generate_precommit_config(precommit_config_path)


def generate_precommit_config(config_file: Path):
    """
    Parse .pre-commit-config.yaml and generate packit-specific configuration
    to it if not already present
    """
    with open(config_file) as f:
        data = yaml.safe_load(f)

    if not is_file_empty(config_file):
        if is_packit_precommit_config_present(data):
            return

        data = prepare_precommit_config(data)

    else:
        # add configuration to empty file
        precommit_config = get_latest_precommit_hook()
        data = {"repos": [precommit_config]}

    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    logger.debug(f"Pre-commit config file '{config_file}' changed.")


def is_packit_precommit_config_present(data):
    """
    Check whether packit-specific configuration is already
    present in .pre-commit-config.yaml
    """
    if not isinstance(data, dict):
        return False

    if "repos" not in data:
        return False

    if not isinstance(data["repos"], list):
        return False

    repos = data["repos"]
    return any(
        repo.get("repo") == PRECOMMIT_CONFIG_TEMPLATE.get("repo")
        # [NOTE] If we introduce more hooks, make sure to check for subset rather than equality.
        # Or drop the check entirely.
        and repo.get("hooks") == PRECOMMIT_CONFIG_TEMPLATE.get("hooks")
        for repo in repos
    )


def prepare_precommit_config(data):
    """
    Go over loaded YAML config file and try to add packit-specific configuration
    Raise an error if there is a problem with the file structure
    """
    precommit_config = get_latest_precommit_hook()

    if isinstance(data, dict) and "repos" in data:
        if isinstance(data["repos"], list):
            data["repos"].append(precommit_config)
        elif isinstance(data["repos"], dict):
            raise PackitException(
                "Unexpected structure of .pre-commit-config.yaml."
                " A list is supposed to follow the 'repos' keyword."
                " Please consult the official pre-commit documentation.",
            )
        else:
            data["repos"] = [precommit_config]
    elif isinstance(data, dict):
        data["repos"] = [precommit_config]
    elif isinstance(data, list):
        raise PackitException(
            "Unexpected structure of .pre-commit-config.yaml:"
            " The root element should be a dictionary."
            " Please consult the official pre-commit documentation.",
        )

    else:
        # other problem with syntax
        raise PackitException(
            "Unexpected structure of .pre-commit-config.yaml."
            " Please consult the official pre-commit documentation.",
        )

    return data


def get_latest_precommit_hook() -> dict:
    """
    Get the latest release of precommit hook and return precommit
    config containing the latest release
    """
    latest_release = get_latest_precommit_hook_release()
    if not latest_release:
        raise PackitException(
            "Something went wrong trying to fetch latest precommit release.",
        )
    precommit_config = PRECOMMIT_CONFIG_TEMPLATE.copy()
    precommit_config["rev"] = latest_release

    return precommit_config
