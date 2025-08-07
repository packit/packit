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

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import (
    cover_packit_exception,
    get_existing_config,
    get_git_repo,
    get_precommit_config,
)
from packit.config import get_context_settings
from packit.config.config import pass_config
from packit.config.package_config import get_local_specfile_path
from packit.constants import (
    PACKIT_CONFIG_TEMPLATE,
    PRECOMMIT_CHECK_REBASE_TEMPLATE,
    PRECOMMIT_VALIDATE_CONFIG,
)
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Reset config to default if already exists.",
)
@pass_config
@cover_packit_exception
def init(
    config,
    path_or_url,
    force,
):
    """
    Create the initial Packit configuration in a repository

    See 'packit source-git init', if you want to initialize a repository
    as a source-git repo.
    """
    working_dir = path_or_url.working_dir
    git_dir = get_git_repo(working_dir)
    if not git_dir:
        raise PackitException(
            " .git repository not found."
            " Initialize current repository as a git repo first.",
        )

    precommit_config_path = get_precommit_config(working_dir)
    if precommit_config_path:
        # TODO url would be valid, but path probably wouldn't....
        append_precommit_config(precommit_config_path, url=path_or_url)
    else:
        raise PackitException(
            " Pre-commit configuration file .pre-commit-config.yaml not found."
            " Please ensure that this file is present.",
            " ",
            " You might also want to install pre-commit. You can use:",
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


def append_precommit_config(config_file: Path, url):
    """
    Append packit-specific configuration to .pre-commit-config.yaml
    """
    check_rebase = PRECOMMIT_CHECK_REBASE_TEMPLATE.format(upstream_url=url)

    with config_file.open("a") as f:
        f.write(check_rebase)
        f.write(PRECOMMIT_VALIDATE_CONFIG)
        logger.debug(f"Pre-commit config file '{config_file}' changed.")
