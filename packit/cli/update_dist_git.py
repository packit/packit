# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Update a dist-git repo from a source-git repo
"""

import pathlib
import click

from packit.config import pass_config
from packit.config.config import Config
from packit.update_dist_git import update_dist_git


@click.command("update-dist-git")
@click.option(
    "--pkg-tool",
    type=str,
    help="""Name or path of the packaging tool used to work with
    sources in the dist-git repo. A variant of 'rpkg'.""",
)
@click.option(
    "-m",
    "--message",
    metavar="<msg>",
    type=str,
    help="""Commit the changes in the dist-git repository and use <msg>
    as the commit message.

    Mutually exclusive with -F.""",
)
@click.option(
    "-F",
    "--file",
    "file_",
    metavar="<file>",
    type=click.Path(exists=True, dir_okay=False, allow_dash=True),
    help="""Commit the changes in the dist-git repository and take the commit message
    from <file>. Use - to read from the standard input.""",
)
@click.argument("source-git", type=click.Path(exists=True, file_okay=False))
@click.argument("dist-git", type=click.Path(exists=True, file_okay=False))
@pass_config
def update_dist_git_cmd(
    config: Config,
    source_git: str,
    dist_git: str,
    pkg_tool: str,
    message: str,
    file_: str,
):
    """Update a dist-git repository using content from a source-git repository

    Update a dist-git repository with patches created from the commits between <upstream_ref> and
    the current HEAD of the source-git repo.

    TODO(csomh): add a description of what this command does and how it works.
    """
    if message and file_:
        raise click.BadOptionUsage("-m", "Option -m cannot be combined with -F.")
    if file_:
        message = pathlib.Path(file_).read_text()

    update_dist_git(
        pathlib.Path(source_git), pathlib.Path(dist_git), config, pkg_tool, message
    )
