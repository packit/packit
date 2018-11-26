import shutil

import click

from transformator import Transformator


@click.command("sg2dg")
@click.option("--upstream-ref")
@click.option("--package-name")
@click.option("--dest-dir")
@click.option("--rev-list-option", multiple=True)
@click.argument("repo")
@click.argument("dist-git")
@click.argument("name")
@click.argument("version")
def sg2dg(upstream_ref, package_name, dest_dir, rev_list_option, repo, dist_git, name, version):
    """
    1. Create tarball from the source git repo.\n
    2. Create patches from the downstream commits.\n
    3. Copy the redhat/ dir to the dist-git.\n
    4. Take the tarball and upload it to lookaside cache.\n
    5. The output is the directory (= dirty git repo)
    """
    try:
        with Transformator(url=repo,
                           upstream_name=name,
                           package_name=package_name,
                           version=version,
                           dest_dir=dest_dir) as t:
            t.clone_dist_git_repo(dist_git_url=dist_git)
            t.create_archive()
            t.copy_redhat_content_to_dest_dir()
            patches = t.create_patches(upstream=upstream_ref, rev_list_option=rev_list_option)
            t.add_patches_to_specfile(patch_list=patches)

            click.echo(f"DEST_DIR: {t.dest_dir}")
    finally:
        # TODO: REMOVE FOLLOWING LINES:
        print(f"Cleaning: {t.dest_dir}")
        shutil.rmtree(t.dest_dir)


if __name__ == '__main__':
    sg2dg()
