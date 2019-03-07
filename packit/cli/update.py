"""
Update selected component from upstream in Fedora
"""

import logging
import os
import sys

import click

from packit.api import PackitAPI
from packit.cli.types import LocalProjectParameter
from packit.config import pass_config, get_context_settings, get_local_package_config
from packit.exceptions import PackitException
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
         "Otherwise clone the repo in a temporary directory.")
@click.option(
    "--upstream-git-path",
    help="Path to the upstream git repository.",
    default=".")
@click.argument("repo", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir))
@pass_config
def update(config, dist_git_path, upstream_git_path, dist_git_branch, repo):
    """
    Release current upstream release into Fedora
    """
    package_config = get_local_package_config(directory=repo.working_dir)
    package_config.downstream_project_url = dist_git_path
    package_config.upstream_project_url = upstream_git_path
    api = PackitAPI(config=config, package_config=package_config)
    try:
        api.sync_release(dist_git_branch)
    except PackitException as exc:
        logger.exception(exc)
        sys.exit(1)
