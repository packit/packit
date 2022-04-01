# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT


"""
Update a source-git repo from a dist-git repo
"""

import pathlib

import click

from packit.config import pass_config
from packit.config import Config, get_local_package_config
from packit.api import PackitAPI
from packit.local_project import LocalProject
from packit.cli.utils import cover_packit_exception


@click.command("update-source-git")
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Don't check the synchronization status of the source-git"
    " and dist-git repos prior to performing the update.",
)
@click.argument("dist-git", type=click.Path(exists=True, file_okay=False))
@click.argument("source-git", type=click.Path(exists=True, file_okay=False))
@click.argument("revision-range", required=False)
@pass_config
@cover_packit_exception
def update_source_git(
    config: Config,
    source_git: str,
    dist_git: str,
    revision_range: str,
    force: bool,
):
    """Update a source-git repository based on a dist-git repository.

    Update a source-git repository with the selected checkout of a spec file
    and additional packaging files from a dist-git repository.

    Revision range represents part of dist-git history which is supposed
    to be synchronized. Use `HEAD~..` if you want to synchronize the last
    commit from dist-git. For more information on possible revision range
    formats, see gitrevisions(7). If the revision range is not specified,
    dist-git commits with no counterpart in source-git will be synchronized.

    If patches or the sources file in the spec file changed, the command
    exits with return code 2. Such changes are not supported by this
    command, code changes should happen in the source-git repo.

    Inapplicable changes to the .gitignore file are ignored since the
    file may not be synchronized between dist-git and source-git.

    This command, by default, performs only local operations and uses the
    content of the source-git and dist-git repositories as it is, no checkout
    or fetch is performed.

    After the synchronization is done, packit will inform about the changes
    it has performed and about differences between source-git and dist-git
    prior to the synchronization process.

    Dist-git commit messages are preserved and used when creating new
    source-git commits, but a 'From-dist-git-commit' trailer is appended
    to them to mark the hash of the dist-git commit from which they
    are created.


    Examples

    Take the extra (not synchronized) commit(s) of systemd dist-git repo and
    copy the spec file and other packaging files into the source-git repo:

    \b
        $ packit source-git update-source-git rpms/systemd src/systemd

    Synchronize changes from the last three dist-git commits:

    \b
        $ packit source-git update-source-git rpms/systemd src/systemd HEAD~3..
    """
    if force and not revision_range:
        raise click.BadOptionUsage(
            "-f", "revision-range has to be specified when -f/--force is used"
        )

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

    api.update_source_git(
        revision_range=revision_range,
        check_sync_status=not force,
    )
