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


@click.command("sync-from-downstream", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch", help="Source branch in dist-git for sync.", default="master"
)
@click.option(
    "--upstream-branch", help="Target branch in upstream to sync to.", default="master"
)
@click.option("--no-pr", is_flag=True, help="Pull request is not create.")
@click.argument(
    "path_or_url", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def sync_from_downstream(config, dist_git_branch, upstream_branch, no_pr, path_or_url):
    """
    Copy synced files from Fedora dist-git into upstream by opening a pull request.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    api.sync_from_downstream(dist_git_branch, upstream_branch, no_pr)
