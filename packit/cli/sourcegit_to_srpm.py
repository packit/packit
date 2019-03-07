import logging
import os

import click

from packit.cli.utils import cover_packit_exception
from packit.config import pass_config, get_context_settings, get_local_package_config
from packit.local_project import LocalProject

logger = logging.getLogger(__file__)


@click.command("srpm", context_settings=get_context_settings())
@click.option("--dest-dir")
@click.option("--upstream-ref")
@click.option("--version")
@click.argument("repo", default=os.path.abspath(os.path.curdir))
@pass_config
@cover_packit_exception
def sg2srpm(config, dest_dir, upstream_ref, version, repo):
    """
    Generate a srpm from packit.

    This script is meant to accept a source git repo with a branch as an input and produce a SRPM.

    It is expected to do this:

    1. clone the repo

    2. create archive out of the sources

    3. create SRPM
    """

    package_config = get_local_package_config()
    sourcegit = LocalProject(git_url=repo)
    if not package_config:
        package_config = get_local_package_config(directory=sourcegit.working_dir)

    distgit = LocalProject(
        git_url=package_config.metadata["dist_git_url"],
        namespace="rpms",
        repo_name=package_config.metadata["package_name"],
        working_dir=dest_dir,
    )

    distgit.working_dir_temporary = False
    with Transformator(
        sourcegit=sourcegit,
        distgit=distgit,
        version=version,
        fas_username=config.fas_user,
        package_config=package_config,
    ) as t:
        t.download_upstream_archive()
        t.copy_synced_content_to_distgit_directory(
            synced_files=package_config.synced_files
        )
        patches = t.create_patches(upstream=upstream_ref)
        t.add_patches_to_specfile(patch_list=patches)
        srpm = t.create_srpm()
        click.echo(srpm)
