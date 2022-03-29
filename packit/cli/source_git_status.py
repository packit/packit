# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""Check synchronization status of source-git and dist-git"""

import pathlib

import click

from packit.config import pass_config
from packit.config import Config, get_local_package_config
from packit.api import PackitAPI
from packit.local_project import LocalProject
from packit.cli.utils import cover_packit_exception


@click.command("status")
@click.argument("source-git", type=click.Path(exists=True, file_okay=False))
@click.argument("dist-git", type=click.Path(exists=True, file_okay=False))
@pass_config
@cover_packit_exception
def source_git_status(config: Config, source_git: str, dist_git: str):
    """Tell the synchronization status of a source-git and a dist-git repo.

    This command checks the commit history in the provided source-git
    and dist-git repos and informs about the range of commits to be
    synchronized from dist-git to source-git or the other way around,
    or informs that the repositories are in sync.

    If possible, the status command also provides instructions on how
    to synchronize the repositories.
    """
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
    click.echo(api.sync_status_string(source_git=source_git, dist_git=dist_git))
