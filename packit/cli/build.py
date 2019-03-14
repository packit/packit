import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings

logger = logging.getLogger(__file__)


@click.command("build", context_settings=get_context_settings())
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
    "--scratch", is_flag=True, default=False, help="Submit a scratch koji build"
)
@click.argument(
    "path_or_url", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def build(config, dist_git_path, dist_git_branch, scratch, path_or_url):
    """
    Build selected upstream project in Fedora.

    Packit goes to dist-git and performs `fedpkg build` for the selected branch.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config, dist_git_path=dist_git_path, local_project=path_or_url
    )
    api.build(dist_git_branch, scratch=scratch)
