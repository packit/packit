import shutil

import click

from transformator import Transformator


@click.command("sg2dg")
@click.option("--upstream-ref")
@click.option("--package-name")
@click.option("--dest-dir")
@click.argument("repo")
@click.argument("dist-git")
@click.argument("name")
@click.argument("version")
def sg2dg(upstream_ref, package_name, dest_dir, repo, dist_git, name, version):
    upstream_ref = upstream_ref or version
    try:
        with Transformator(url=repo,
                           upstream_name=name,
                           package_name=package_name,
                           version=version,
                           dest_dir=dest_dir) as t:
            t.clone_dist_git_repo(dist_git_url=dist_git)
            t.create_archive()
            patches = t.create_patches(upstream=upstream_ref)
            t.add_patches_to_specfile(patch_list=patches)

            click.echo(f"DEST_DIR: {t.dest_dir}")
    finally:
        # TODO: REMOVE FOLLOWING LINES:
        print(f"Cleaning: {t.dest_dir}")
        shutil.rmtree(t.dest_dir)


if __name__ == '__main__':
    sg2dg()
