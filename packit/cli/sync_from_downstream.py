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

logger = logging.getLogger(__file__)


@click.command("sync-from-downstream", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Source branch in dist-git to sync from.",
    default="master",
)
@click.option(
    "--upstream-branch", help="Target branch in upstream to sync to.", default="master"
)
@click.option(
    "--no-pr", is_flag=True, help="Do not create a pull request to upstream repository."
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
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(remote_param_name="remote"),
    default=os.path.abspath(os.path.curdir),
)
@cover_packit_exception
@pass_config
def sync_from_downstream(
    config, dist_git_branch, upstream_branch, no_pr, path_or_url, fork, remote
):
    """
    Copy synced files from Fedora dist-git into upstream by opening a pull request.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    api.sync_from_downstream(
        dist_git_branch, upstream_branch, no_pr=no_pr, fork=fork, remote_name=remote
    )
