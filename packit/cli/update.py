"""
Update selected component from upstream in Fedora
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings

logger = logging.getLogger(__file__)


@click.command("propose-update", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Target branch in dist-git to release into.",
    default="master",
)
@click.option(
    "--dist-git-path",
    help="Path to dist-git repo to work in. "
    "Otherwise clone the repo in a temporary directory.",
)
@click.argument(
    "repo", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@click.argument("version", required=False)
@pass_config
@cover_packit_exception
def update(config, dist_git_path, dist_git_branch, repo, version):
    """
    Release current upstream release into Fedora

    REPO argument is a local path to the upstream git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """
    api = get_packit_api(config=config, dist_git_path=dist_git_path, repo=repo)
    api.sync_release(dist_git_branch, version=version)
