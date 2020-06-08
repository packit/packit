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

import logging
from os import getcwd

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.config.aliases import get_branches
from packit.exceptions import PackitCommandFailedError, ensure_str

logger = logging.getLogger(__name__)


@click.command("build", context_settings=get_context_settings())
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
    "--from-upstream",
    help="Build the project in koji directly from the upstream repository",
    is_flag=True,
    default=False,
)
@click.option(
    "--koji-target", help="Koji target to build inside (see `koji list-targets`)."
)
@click.option(
    "--scratch", is_flag=True, default=False, help="Submit a scratch koji build"
)
@click.option("--nowait", is_flag=True, default=False, help="Don't wait on build")
@click.argument("path_or_url", type=LocalProjectParameter(), default=getcwd())
@pass_config
@cover_packit_exception
def build(
    config,
    dist_git_path,
    dist_git_branch,
    from_upstream,
    scratch,
    nowait,
    path_or_url,
    koji_target,
):
    """
    Build selected upstream project in Fedora.

    By default, packit checks out the respective dist-git repository and performs
    `fedpkg build` for the selected branch. With `--from-upstream`, packit creates a SRPM
    out of the current checkout and sends it to koji.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config, dist_git_path=dist_git_path, local_project=path_or_url
    )

    branches_to_build = get_branches(*dist_git_branch.split(","), default="master")
    click.echo(f"Building for the following branches: {', '.join(branches_to_build)}")

    for branch in branches_to_build:
        try:
            out = api.build(
                dist_git_branch=branch,
                scratch=scratch,
                nowait=nowait,
                koji_target=koji_target,
                from_upstream=from_upstream,
            )
        except PackitCommandFailedError as ex:
            logs_stdout = "\n>>> ".join(ex.stdout_output.strip().split("\n"))
            logs_stderr = "\n!!! ".join(ex.stderr_output.strip().split("\n"))
            click.echo(
                f"Build for branch '{branch}' failed. \n"
                f">>> {logs_stdout}\n"
                f"!!! {logs_stderr}\n",
                err=True,
            )
        else:
            if out:
                print(ensure_str(out))
