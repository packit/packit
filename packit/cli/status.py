"""
Display status
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import pass_config, get_context_settings
from packit.cli.utils import get_packit_api

logger = logging.getLogger(__file__)


@click.command("status", context_settings=get_context_settings())
@click.argument(
    "path_or_url", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def status(config, path_or_url):
    """
    Display status
    """

    api = get_packit_api(config=config, local_project=path_or_url)

    api.status()
