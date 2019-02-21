import logging
import os

import click

from packit.config import get_context_settings, pass_config, get_local_package_config
from packit.local_project import LocalProject
from packit.transformator import Transformator

logger = logging.getLogger(__file__)


@click.command("update", context_settings=get_context_settings())
@click.option("--dest-dir")
@click.option("--version")
@click.argument("repo", default=os.path.abspath(os.path.curdir))
@pass_config
def update(config, dest_dir, version, repo):
    """
    1. Take the release

    2. Update the distgit content

    3. Create a PR on distgit
    """
    package_config = get_local_package_config()
    sourcegit = LocalProject(git_url=repo)
    if not package_config:
        package_config = get_local_package_config(directory=sourcegit.working_dir)

    if not package_config:
        raise Exception("No package config found.")

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
        upstream_version = version or t.get_latest_upstream_version()
        t.distgit_spec.set_version(version=upstream_version)
        t.download_upstream_archive()

        # TODO: @TomasTomecek will add the missing code here...
