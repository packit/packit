# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Display status
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import get_context_settings, pass_config
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)

logger = logging.getLogger(__name__)


@click.command("status", context_settings=get_context_settings())
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="update"),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
@iterate_packages
def status(config, path_or_url, package_config):
    """
    Display status.

    \b
    - latest downstream pull requests
    - versions from all downstream branches
    - latest upstream releases
    - latest builds in Koji
    - latest builds in Copr
    - latest updates in Bodhi
    """

    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )
    api.status()
