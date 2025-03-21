# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Validate PackageConfig
"""

import logging
import os

import click

from packit.api import PackitAPI
from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


@click.command("validate", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "--offline",
    default=False,
    is_flag=True,
    help="Do not make remote API calls requiring network access.",
)
@cover_packit_exception
def validate_config(path_or_url: LocalProject, offline: bool):
    """
    Validate PackageConfig.

    \b
    - checks missing values
    - checks incorrect types
    - checks whether monitoring is enabled if 'pull_from_upstream` is used

    PATH_OR_URL argument is a local path or a URL to a git repository with packit configuration file
    """
    output = PackitAPI.validate_package_config(path_or_url.working_dir, offline)
    logger.info(output)
    # TODO: print more if config.debug
