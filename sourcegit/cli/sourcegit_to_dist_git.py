import logging

import click

from sourcegit.config import pass_config, get_context_settings
from sourcegit.transformator import Transformator

logger = logging.getLogger("source_git")


@click.command("distgit", context_settings=get_context_settings())
@click.option("--dest-dir")
@click.option("--no-new-sources", is_flag=True)
@click.option("--package-name")
@click.option("--rev-list-option", multiple=True)
@click.option("--upstream-ref")
@click.argument("repo")
@click.argument("dist-git")
@click.argument("name")
@click.argument("version")
@pass_config
def sg2dg(config,
          dest_dir,
          no_new_sources,
          package_name,
          rev_list_option,
          upstream_ref,
          repo,
          dist_git,
          name,
          version):
    """
    Convert sourcegit to distgit.

    1. Create tarball from the source git repo.

    2. Create patches from the downstream commits.

    3. Copy the redhat/ dir to the dist-git.

    4. Take the tarball and upload it to lookaside cache.

    5. The output is the directory (= dirty git repo)
    """

    with Transformator(url=repo,
                       upstream_name=name,
                       package_name=package_name,
                       version=version,
                       dest_dir=dest_dir,
                       dist_git_url=dist_git,
                       fas_username=config.fas_user,
                       rev_list_option=rev_list_option) as t:
        t.clone_dist_git_repo()
        t.create_archive()
        t.copy_redhat_content_to_dest_dir()
        patches = t.create_patches(upstream=upstream_ref)
        t.add_patches_to_specfile(patch_list=patches)
        if not no_new_sources:
            t.upload_archive_to_lookaside_cache(config.keytab)
        else:
            logger.debug("Skipping fedpkg new-sources.")
        click.echo(f"{t.dest_dir}")
