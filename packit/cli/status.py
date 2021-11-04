# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Display status
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.cli.utils import get_packit_api
from packit.config import pass_config, get_context_settings

logger = logging.getLogger(__name__)


@click.command("status", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
def status(config, path_or_url):
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

    api = get_packit_api(config=config, local_project=path_or_url)
    api.status()
