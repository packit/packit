import logging

import click
from pkg_resources import get_distribution

from packit.cli.build import build
from packit.cli.create_update import create_update
from packit.cli.srpm import srpm
from packit.cli.update import update
from packit.cli.sync_from_downstream import sync_from_downstream
from packit.cli.watch_upstream_release import watch_releases
from packit.cli.status import status
from packit.config import Config, get_context_settings
from packit.utils import set_logging

logger = logging.getLogger("packit")


@click.group("packit", context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True)
@click.option("--fas-user", help="Fedora Account System username.")
@click.option("-k", "--keytab", help="Path to FAS keytab file.")
@click.pass_context
def packit_base(ctx, debug, fas_user, keytab):
    c = Config.get_user_config()
    c.debug = debug or c.debug
    c.fas_user = fas_user or c.fas_user
    c.keytab_path = keytab or c.keytab_path
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
    click.echo(get_distribution("packitos").version)


# packit_base.add_command(sg2dg)
# packit_base.add_command(sg2srpm)
# packit_base.add_command(watcher)
packit_base.add_command(version)
# packit_base.add_command(watch_pr)
packit_base.add_command(watch_releases)
packit_base.add_command(update)
packit_base.add_command(sync_from_downstream)
packit_base.add_command(build)
packit_base.add_command(create_update)
packit_base.add_command(srpm)
packit_base.add_command(status)

if __name__ == "__main__":
    packit_base()
