# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Generate initial configuration for packit
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
import ruamel.yaml

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import (
    cover_packit_exception,
    get_existing_config,
    get_precommit_config,
    is_file_empty,
)
from packit.config import get_context_settings
from packit.config.config import pass_config
from packit.config.package_config import get_local_specfile_path
from packit.constants import (
    PACKIT_CONFIG_TEMPLATE,
    PRECOMMIT_CONFIG,
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
    "--with_precommit",
    default=False,
    is_flag=True,
    help="Automatically creates an empty precommit configuration file if missing.",
)
@pass_config
@cover_packit_exception
def init(config, path_or_url, force, with_precommit):
    """
    Create the initial Packit configuration in a repository

    See 'packit source-git init', if you want to initialize a repository
    as a source-git repo.
    """
    working_dir = path_or_url.working_dir
    precommit_config_path = None

    if is_git_repo(working_dir):
        raise PackitException(
            " .git repository not found."
            " Initialize current repository as a git repo first in order"
            " to set up Packit config validation upon pre-commit.",
        )

    if with_precommit:
        precommit_config_path = working_dir / ".pre-commit-config.yaml"
        precommit_config_path.touch()
    else:
        precommit_config_path = get_precommit_config(working_dir)

    if precommit_config_path:
        generate_precommit_config(precommit_config_path)
    else:
        raise PackitException(
            " Pre-commit configuration file .pre-commit-config.yaml not found."
            " This file is necessary to set up Packit config validation."
            " Please ensure that it is present."
            " "
            " You might also want to install pre-commit. You can use:"
            " `pip install pre-commit && pre-commit install`",
        )

    config_path = get_existing_config(working_dir)
    if config_path:
        if not force:
            raise PackitException(
                f"Packit config {config_path} already exists."
                " If you want to regenerate it use `packit init --force`",
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


def generate_precommit_config(config_file: Path):
    """
    Parse .pre-commit-config.yaml and generate packit-specific configuration
    to it if not already present
    """
    yaml = ruamel.yaml.YAML()
    data = yaml.load(config_file)

    if not is_file_empty(config_file):
        if is_precommit_config_present(data):
            return

        data = prepare_precommit_config(data)

    else:
        # add configuration to empty file
        data = {"repos": [PRECOMMIT_CONFIG]}

    yaml.dump(data, sys.stdout)  # testing purposes

    with open(config_file, "w") as f:
        yaml.dump(data, f)

    logger.debug(f"Pre-commit config file '{config_file}' changed.")


def is_precommit_config_present(data):
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

    return PRECOMMIT_CONFIG in data["repos"]


def prepare_precommit_config(data):
    """
    Go over loaded YAML config file and try to append packit-specific configuration
    Raise an error if there is a problem with the file structure
    """
    if isinstance(data, dict) and "repos" in data:
        if isinstance(data["repos"], list):
            data["repos"].append(PRECOMMIT_CONFIG)
        elif isinstance(data["repos"], dict):
            print(
                " Unexpected structure of .pre-commit-config.yaml."
                " A list is supposed to follow the 'repos' keyword."
                " Please consult the official pre-commit documentation.",
            )
        else:
            data["repos"] = [PRECOMMIT_CONFIG]
    elif isinstance(data, dict):
        data["repos"] = [PRECOMMIT_CONFIG]
    elif isinstance(data, list):
        raise PackitException(
            " Unexpected structure of .pre-commit-config.yaml:"
            " The root element should be a dictionary."
            " Please consult the official pre-commit documentation.",
        )

    else:
        # other problem with syntax
        raise PackitException(
            " Unexpected structure of .pre-commit-config.yaml."
            " Please consult the official pre-commit documentation.",
        )

    return data
