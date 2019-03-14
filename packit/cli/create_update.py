import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.constants import DEFAULT_BODHI_NOTE

logger = logging.getLogger(__file__)


@click.command("create-update", context_settings=get_context_settings())
@click.option("--dist-git-branch", help="Target branch in dist-git to release into.")
@click.option(
    "--koji-build",
    help="Koji build to add to the bodhi update (can be specified multiple times)",
    required=False,
    multiple=True,
)
# It would make sense to open an editor here,
# just like `git commit` and get notes like that
@click.option(
    "--update-notes",
    help="Bodhi update notes",
    required=False,
    default=DEFAULT_BODHI_NOTE,
)
@click.option(
    "--update-type",
    type=click.types.Choice(("security", "bugfix", "enhancement", "newpackage")),
    help="Type of the bodhi update",
    required=False,
    default="enhancement",
)
@click.argument(
    "repo", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def create_update(config, dist_git_branch, koji_build, update_notes, update_type, repo):
    """
    Create a bodhi update for the selected upstream project

    REPO argument is a local path to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, repo=repo)
    api.create_update(
        koji_builds=koji_build,
        dist_git_branch=dist_git_branch,
        update_notes=update_notes,
        update_type=update_type,
    )
