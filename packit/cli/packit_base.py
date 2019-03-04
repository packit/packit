import logging

import click
from pkg_resources import get_distribution

import packit
from packit.cli.update import update
from packit.cli.sourcegit_to_dist_git import sg2dg
from packit.cli.sourcegit_to_srpm import sg2srpm
from packit.cli.watch_fedora_ci import watcher
from packit.cli.watch_sg_pr import watch_pr
from packit.cli.watch_upstream_release import watch_releases
from packit.config import Config, get_context_settings
from packit.utils import set_logging

logger = logging.getLogger(__name__)


@click.group("packit", context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True)
@click.option("--fas-user", help="Fedora Account System username.")
@click.option("-k", "--keytab", help="Path to FAS keytab file.")
@click.pass_context
def packit_base(ctx, debug, fas_user, keytab):
    c = Config()
    c.debug = debug
    c.fas_user = fas_user
    c.keytab_path = keytab
    ctx.obj = c
    if ctx.obj.debug:
        set_logging(level=logging.DEBUG)
        logger.debug("logging set to DEBUG")
    else:
        set_logging(level=logging.INFO)
        logger.debug("logging set to INFO")


@click.command("version")
def version():
    """Display the version."""
    click.echo(get_distribution('packitos').version)


packit_base.add_command(sg2dg)
packit_base.add_command(sg2srpm)
packit_base.add_command(watcher)
packit_base.add_command(version)
packit_base.add_command(watch_pr)
packit_base.add_command(watch_releases)
packit_base.add_command(update)

if __name__ == "__main__":
    packit_base()
