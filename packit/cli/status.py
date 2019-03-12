"""
Display status
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import pass_config, get_context_settings, get_local_package_config
from rebasehelper.specfile get_full_version

logger = logging.getLogger(__file__)


@click.command("status", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Target branch in dist-git to release into.",
    default="master",
)
@click.argument(
    "repo", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def status():
    """
    Display status
    """
