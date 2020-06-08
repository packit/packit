# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
    "(defaults to 'master')",
    default="master",
)
@click.option(
    "--upstream-branch", help="Target branch in upstream to sync to.", default="master"
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
    "--remote",
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
    type=LocalProjectParameter(remote_param_name="remote"),
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
    remote,
    exclude,
    force,
):
    """
    Copy synced files from Fedora dist-git into upstream by opening a pull request.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)

    branches_to_sync = get_branches(*dist_git_branch.split(","), default="master")
    click.echo(f"Syncing from the following branches: {', '.join(branches_to_sync)}")

    for branch in branches_to_sync:
        api.sync_from_downstream(
            dist_git_branch=branch,
            upstream_branch=upstream_branch,
            no_pr=no_pr,
            fork=fork,
            remote_name=remote,
            exclude_files=exclude,
            force=force,
        )
