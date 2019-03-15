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
@click.option(
    "--local-content",
    is_flag=True,
    default=False,
    help="Do not checkout release tag. Use the current state of the repo.",
)
@click.option(
    "--force-new-sources",
    is_flag=True,
    default=False,
    help="Upload the new sources also when the archive is already in the lookaside cache.",
)
@click.argument(
    "path_or_url", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@click.argument("version", required=False)
@pass_config
@cover_packit_exception
def update(
    config,
    dist_git_path,
    dist_git_branch,
    force_new_sources,
    local_content,
    path_or_url,
    version,
):
    """
    Release current upstream release into Fedora

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """
    api = get_packit_api(config=config, dist_git_path=dist_git_path, local_project=path_or_url)
    api.sync_release(
        dist_git_branch,
        use_local_content=local_content,
        version=version,
        force_new_sources=force_new_sources,
    )
