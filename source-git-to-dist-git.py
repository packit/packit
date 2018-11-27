import logging

import click

from transformator import Transformator
from utils import _set_logging

logger = logging.getLogger("source_git")

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'],
                        auto_envvar_prefix='SOURCE_GIT')


@click.command("sg2dg", context_settings=CONTEXT_SETTINGS)
@click.option("-d", "--debug", is_flag=True)
@click.option("--dest-dir")
@click.option("--fas-user")
@click.option("-k", "--keytab")
@click.option("--no-new-sources", is_flag=True)
@click.option("--package-name")
@click.option("--rev-list-option", multiple=True)
@click.option("--upstream-ref")
@click.option("-v", "--verbose", is_flag=True)
@click.argument("repo")
@click.argument("dist-git")
@click.argument("name")
@click.argument("version")
def sg2dg(debug,
          dest_dir,
          fas_user,
          keytab,
          no_new_sources,
          package_name,
          rev_list_option,
          upstream_ref,
          verbose,
          repo,
          dist_git,
          name,
          version):
    """
    1. Create tarball from the source git repo.\n
    2. Create patches from the downstream commits.\n
    3. Copy the redhat/ dir to the dist-git.\n
    4. Take the tarball and upload it to lookaside cache.\n
    5. The output is the directory (= dirty git repo)
    """
    if verbose:
        _set_logging(level=logging.INFO,
                     format="%(message)s")

    if debug:
        _set_logging(level=logging.DEBUG)

    with Transformator(url=repo,
                       upstream_name=name,
                       package_name=package_name,
                       version=version,
                       dest_dir=dest_dir,
                       dist_git_url=dist_git,
                       fas_username=fas_user) as t:
        t.clone_dist_git_repo()
        t.create_archive()
        t.copy_redhat_content_to_dest_dir()
        patches = t.create_patches(upstream=upstream_ref, rev_list_option=rev_list_option)
        t.add_patches_to_specfile(patch_list=patches)
        if not no_new_sources:
            t.upload_archive_to_lookaside_cache(keytab)
        else:
            logger.debug("Skipping fedpkg new-sources.")
        click.echo(f"{t.dest_dir}")


if __name__ == '__main__':
    sg2dg()
