import logging

import click

from sourcegit.config import pass_config, get_context_settings
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
def sg2srpm(config,
            dest_dir,
            package_name,
            rev_list_option,
            upstream_ref,
            repo,
            dist_git,
            name,
            version):
    """
    Generate a srpm from sourcegit.

    This script is meant to accept a source git repo with a branch as an input and produce a SRPM.

    It is expected to do this:

    1. clone the repo

    2. create archive out of the sources

    3. create SRPM
    """

    with Transformator(url=repo,
                       upstream_name=name,
                       package_name=package_name,
                       version=version,
                       dest_dir=dest_dir,
                       dist_git_url=dist_git,
                       branch=upstream_ref,
                       fas_username=config.fas_user) as t:
        t.clone_dist_git_repo()
        t.create_archive()
        """
        t.copy_redhat_content_to_dest_dir()
        patches = t.create_patches(upstream=upstream_ref, rev_list_option=rev_list_option)
        t.add_patches_to_specfile(patch_list=patches)
        """
        t.create_srpm()
        click.echo(f"{t.archive}")
