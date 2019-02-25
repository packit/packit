"""
Update selected component from upstream in Fedora
"""

import logging

import click

from packit.api import PackitAPI
from packit.config import pass_config, get_context_settings, get_local_package_config
from packit.local_project import LocalProject
from packit.transformator import Transformator

logger = logging.getLogger(__file__)


@click.command("propose-update", context_settings=get_context_settings())
@click.option("--dist-git-branch",
              help="Target branch in dist-git to release into.",
              default="master"
              )
@click.option("--dist-git-path",
              help="Path to dist-git repo to work in.")
@pass_config
def update(config, dist_git_path, dist_git_branch):
    """
    Release current upstream release into Fedora
    """
    api = PackitAPI(config)
    api.update(dist_git_branch, dist_git_path=dist_git_path)
