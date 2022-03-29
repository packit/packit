# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Update a dist-git repo from a source-git repo
"""

import pathlib
from shutil import which

import click

from typing import Optional

from packit.cli.utils import cover_packit_exception
from packit.config import pass_config
from packit.config import Config, get_local_package_config
from packit.api import PackitAPI
from packit.local_project import LocalProject


@click.command("update-dist-git")
@click.option(
    "--upstream-ref",
    type=str,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--pkg-tool",
    type=str,
    help="""Name or path of the packaging tool used to work with
    sources in the dist-git repo. A variant of 'rpkg'.

    Skip retrieving and uploading source archives to the lookaside cache
    if not specified.
    """,
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
    metavar="<file>",
    type=click.Path(exists=True, dir_okay=False, allow_dash=True),
    help="""Commit the changes in the dist-git repository and take the commit message
    from <file>. Use - to read from the standard input.""",
)
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Don't check the synchronization status of the source-git"
    " and dist-git repos prior to performing the update.",
)
@click.argument("source-git", type=click.Path(exists=True, file_okay=False))
@click.argument("dist-git", type=click.Path(exists=True, file_okay=False))
@pass_config
@cover_packit_exception
def update_dist_git(
    config: Config,
    source_git: str,
    dist_git: str,
    upstream_ref: Optional[str],
    pkg_tool: Optional[str],
    message: Optional[str],
    file: Optional[str],
    force: Optional[bool],
):
    """Update a dist-git repository using content from a source-git repository

    Update a dist-git repository with patches created from the commits
    between <upstream_ref> and the current HEAD of the source-git repo.

    This command, by default, performs only local operations and uses
    the content of the source-git and dist-git repository as it is:
    does not checkout branches or fetches remotes.

    A commit in dist-git is created only if a commit message is provided with
    --message or --file. This commit will have a 'From-source-git-commit'
    Git-trailer appended to it, to mark the hash of the source-git commit
    from which it is created.

    The source archives are retrieved from the upstream URLs specified in
    the spec-file and uploaded to the lookaside cache in dist-git only if
    '--pkg-tool' is specified.

    Examples:

    To update a dist-git repo from source-git without uploading the source-archive
    to the lookaside cache and creating a commit with the updates, run:

    \b
        $ packit source-git update-dist-git src/curl rpms/curl


    To also commit the changes and upload the source-archive to the lookaside-cache
    specify -m and --pkg-tool:

    \b
        $ packit source-git update-dist-git -m'Update from source-git' \\
                --pkg-tool fedpkg src/curl rpms/curl
    """
    if message and file:
        raise click.BadOptionUsage("-m", "Option -m cannot be combined with -F.")
    if pkg_tool and not which(pkg_tool):
        raise click.BadOptionUsage(
            "--pkg-tool", f"{pkg_tool} is not executable or in any path"
        )
    if file:
        with click.open_file(file, "r") as fp:
            message = fp.read()

    source_git_path = pathlib.Path(source_git).resolve()
    dist_git_path = pathlib.Path(dist_git).resolve()
    package_config = get_local_package_config(
        source_git_path, package_config_path=config.package_config_path
    )
    api = PackitAPI(
        config=config,
        package_config=package_config,
        upstream_local_project=LocalProject(working_dir=source_git_path, offline=True),
        downstream_local_project=LocalProject(working_dir=dist_git_path, offline=True),
    )

    title, _, message = message.partition("\n\n") if message else (None, None, None)
    api.update_dist_git(
        version=None,
        upstream_ref=upstream_ref or package_config.upstream_ref,
        # Add new sources if a pkg_tool was specified.
        add_new_sources=bool(pkg_tool),
        force_new_sources=False,
        upstream_tag=None,
        commit_title=title,
        commit_msg=message,
        sync_default_files=False,
        pkg_tool=pkg_tool,
        mark_commit_origin=True,
        check_sync_status=not force,
    )
