import logging
import os

import click

from packit.config import pass_config, get_context_settings, get_local_package_config
from packit.local_project import LocalProject
from packit.transformator import Transformator

logger = logging.getLogger(__file__)


@click.command("sg2dg", context_settings=get_context_settings())
@click.option("--dest-dir")
@click.option("--no-new-sources", is_flag=True)
@click.option("--upstream-ref")
@click.option("--version")
@click.argument("repo", default=os.path.abspath(os.path.curdir))
@pass_config
def sg2dg(config, dest_dir, no_new_sources, upstream_ref, version, repo):
    """
    Convert source-git repo to dist-git repo.

    1. Create tarball from the source git repo.

    2. Create patches from the downstream commits.

    3. Copy the redhat/ dir to the dist-git.

    4. Take the tarball and upload it to lookaside cache.

    5. The output is the directory (= dirty git repo)
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
        if not no_new_sources:
            t.upload_archive_to_lookaside_cache(config.keytab)
        else:
            logger.debug("Skipping fedpkg new-sources.")
        click.echo(f"{distgit.working_dir}")
