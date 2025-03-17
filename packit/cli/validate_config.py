# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Validate PackageConfig
"""

import logging
import os
from pathlib import Path

import click
import yaml

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings
from packit.config.package_config import find_packit_yaml, load_packit_yaml
from packit.config.package_config_validator import PackageConfigValidator
from packit.local_project import LocalProject
from packit.utils.logging import set_logging

logger = logging.getLogger(__name__)


@click.command("validate-config", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "--offline",
    default=False,
    is_flag=True,
    help="Do not make remote API calls requiring network access.",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Path to a specific Packit configuration file.",
)
@cover_packit_exception
def validate_config(path_or_url: LocalProject, offline: bool, config: str = None, debug: bool = None):
    """
    Validate PackageConfig.

    \b
    - checks missing values
    - checks incorrect types
    - checks whether monitoring is enabled if 'pull_from_upstream' is used

    PATH_OR_URL argument is a local path or a URL to a git repository with a packit configuration file.
    """
    config_path = (
        Path(config)
        if config
        else find_packit_yaml(path_or_url.working_dir, try_local_dir_last=True)
    )

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return

    logger.info(f"Validating config file: {config_path}")

    try:
        config_content = load_packit_yaml(config_path)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file: {e}")
        return

    validator = PackageConfigValidator(
        config_path, config_content, path_or_url.working_dir, offline
    )

    output = validator.validate()
    logger.info(output)

    # TODO: print more if config.debug
