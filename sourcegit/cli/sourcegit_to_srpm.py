import click

from sourcegit.config import pass_config, get_context_settings
from sourcegit.transformator import Transformator


@click.command("srpm", context_settings=get_context_settings())
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
    Generate srpm from sourcegit.

    This script is meant to accept source git repo with a branch as an input and build it in Fedora.

    It is expected to do this:

    1. clone the repo

    2. create archive out of the sources

    3. create SRPM

    4. (x) submit the SRPM to koji

    5. (x) wait for the build to finish

    6. (x) update github status to reflect the result of the build
    """

    with Transformator(url=repo,
                       upstream_name=name,
                       package_name=package_name,
                       version=version,
                       dest_dir=dest_dir,
                       dist_git_url=dist_git,
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
