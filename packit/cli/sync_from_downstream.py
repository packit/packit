# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Update selected component from upstream in Fedora
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.config.aliases import get_branches

logger = logging.getLogger(__name__)


@click.command("sync-from-downstream", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Comma separated list of target branches in dist-git to sync from. "
    "(defaults to repo's default branch)",
)
@click.option(
    "--upstream-branch",
    help="Target branch in upstream to sync to. (defaults to repo's default branch)",
)
@click.option(
    "--no-pr",
    is_flag=True,
    default=False,
    help="Do not create a pull request to upstream repository.",
)
@click.option(
    "--fork/--no-fork",
    is_flag=True,
    default=True,
    help="Push to a fork before creating a pull request.",
)
@click.option(
    "--remote-to-push",
    default=None,
    help=(
        "Name of the remote where packit should push. "
        "If this is not specified, push to a fork if the repo can be forked."
    ),
)
@click.option(
    "--force",
    "-f",
    default=False,
    is_flag=True,
    help="Don't discard changes in the git repo by default, unless this is set.",
)
@click.option("-x", "--exclude", help="File to exclude from sync", multiple=True)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@cover_packit_exception
@pass_config
def sync_from_downstream(
    config,
    dist_git_branch,
    upstream_branch,
    no_pr,
    path_or_url,
    fork,
    remote_to_push,
    exclude,
    force,
):
    """
    Copy synced files from Fedora dist-git into upstream by opening a pull request.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    default_dg_branch = api.dg.local_project.git_project.default_branch
    dist_git_branch = dist_git_branch or default_dg_branch
    branches_to_sync = get_branches(
        *dist_git_branch.split(","), default_dg_branch=default_dg_branch
    )
    click.echo(f"Syncing from the following branches: {', '.join(branches_to_sync)}")

    for branch in branches_to_sync:
        api.sync_from_downstream(
            dist_git_branch=branch,
            upstream_branch=upstream_branch,
            no_pr=no_pr,
            fork=fork,
            remote_name=remote_to_push,
            exclude_files=exclude,
            force=force,
        )
