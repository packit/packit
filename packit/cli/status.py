"""
Display status
"""

import logging

import click

from packit.cli.utils import cover_packit_exception
from packit.config import pass_config, get_context_settings, get_local_package_config
from packit.distgit import DistGit
from packit.upstream import Upstream

logger = logging.getLogger(__file__)


@click.command("status", context_settings=get_context_settings())
@pass_config
@cover_packit_exception
def status(config):
    """
    Display status
    """
    package_config = get_local_package_config()

    up = Upstream(config=config, package_config=package_config)
    dg = DistGit(config=config, package_config=package_config)

    click.echo("Downstream PRs:")
    for pr in dg.local_project.git_project.get_pr_list():
        click.echo(f"#{pr.id} {pr.title} {pr.url}")

    click.echo("Dist-git versions:")
    branches = ["master", "f30", "f29"]
    for branch in branches:
        dg.checkout_branch(git_ref=branch)
        click.echo(f"{branch}: {dg.specfile.get_full_version()}")

    click.echo("GitHub upstream releases:")
    for release in up.local_project.git_project.get_releases():
        click.echo(f"#{release.tag_name}")

    click.echo("Latest builds:")

    # https://github.com/fedora-infra/bodhi/issues/3058
    from bodhi.client.bindings import BodhiClient, BodhiClientException

    b = BodhiClient()

    builds_d = b.latest_builds(dg.package_name)
    print(builds_d)

    builds_str = "\n".join(f" - {b}" for b in builds_d)
    logger.debug(f"Koji builds for package {dg.package_name}: \n{builds_str}")

    for branch in branches:
        koji_tag = f"{branch}-updates-candidate"
        try:
            koji_builds = [builds_d[koji_tag]]
            koji_builds_str = "\n".join(f" - {b}" for b in koji_builds)
            click.echo(
                f"Koji builds for package {dg.package_name} and koji tag {koji_tag}:"
                f"\n{koji_builds_str}"
            )
        except KeyError:
            click.echo(f"No koji builds for package {dg.package_name} and koji tag {koji_tag}")
