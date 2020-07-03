# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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


@click.command("propose-update", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Comma separated list of target branches in dist-git to release into. "
    "(defaults to 'master')",
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
@click.option(
    "--no-pr",
    is_flag=True,
    default=False,
    help="Do not create a pull request to downstream repository.",
)
@click.option(
    "--remote",
    default=None,
    help=(
        "Name of the remote to discover upstream project URL, "
        "If this is not specified, default to origin."
    ),
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--force",
    "-f",
    default=False,
    is_flag=True,
    help="Don't discard changes in the git repo by default, unless this is set.",
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(remote_param_name="remote"),
    default=os.path.curdir,
)
@click.argument("version", required=False)
@pass_config
@cover_packit_exception
def update(
    config,
    dist_git_path,
    dist_git_branch,
    force_new_sources,
    no_pr,
    local_content,
    path_or_url,
    upstream_ref,
    version,
    remote,  # click introspects this in LocalProjectParameter
    force,
):
    """
    Release current upstream release into Fedora

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """
    api = get_packit_api(
        config=config, dist_git_path=dist_git_path, local_project=path_or_url
    )
    branches_to_update = get_branches(*dist_git_branch.split(","), default="master")
    click.echo(f"Syncing from the following branches: {', '.join(branches_to_update)}")

    for branch in branches_to_update:
        api.sync_release(
            dist_git_branch=branch,
            use_local_content=local_content,
            version=version,
            force_new_sources=force_new_sources,
            upstream_ref=upstream_ref,
            create_pr=not no_pr,
            force=force,
        )
