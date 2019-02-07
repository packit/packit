import logging

import click

from sourcegit.config import pass_config, get_context_settings, get_local_package_config
from sourcegit.transformator import Transformator

logger = logging.getLogger(__name__)


@click.command("srpm", context_settings=get_context_settings())
@click.option("--dest-dir")
# @click.option("--no-new-sources", is_flag=True)
@click.option("--package-name")
@click.option("--rev-list-option", multiple=True)
@click.option("--upstream-ref")
@click.argument("repo")
@click.argument("dist-git")
@click.argument("name")
@click.argument("version")
@pass_config
def sg2srpm(config, dest_dir, upstream_ref, repo, version):
    """
    Generate a srpm from sourcegit.

    This script is meant to accept a source git repo with a branch as an input and produce a SRPM.

    It is expected to do this:

    1. clone the repo

    2. create archive out of the sources

    3. create SRPM
    """

    package_config = get_local_package_config()
    with Transformator(
        url=repo,
        version=version,
        dest_dir=dest_dir,
        branch=upstream_ref,
        fas_username=config.fas_user,
        package_config=package_config,
    ) as t:
        t.clone_dist_git_repo()
        t.create_archive()
        t.copy_synced_content_to_dest_dir(synced_files=package_config.synced_files)
        patches = t.create_patches(upstream=upstream_ref)
        t.add_patches_to_specfile(patch_list=patches)
        t.create_srpm()
        click.echo(f"{t.archive}")
