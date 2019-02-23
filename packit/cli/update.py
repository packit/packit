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


@click.command("update", context_settings=get_context_settings())
@click.option("--no-new-sources", is_flag=True)
@click.option("--upstream-ref")
@click.option("--dist-git-branch",
              help="Target branch in dist-git to release into.",
              default="master"
              )
@click.option("--dist-git-path",
              help="Path to dist-git repo to work in.")
@click.argument("version", required=False)
@click.argument("repo", required=False)
@pass_config
def update(config, dist_git_path, dist_git_branch, no_new_sources, upstream_ref, repo, version):
    """
    Release current upstream release into Fedora

    :param config:
    :param dest_dir:
    :param no_new_sources:
    :param upstream_ref:
    :param repo:
    :param version:
    :return:
    """
    api = PackitAPI(config)
    api.update(dist_git_branch, dist_git_path=dist_git_path)
