import logging

import click

import sourcegit
from sourcegit.cli.sourcegit_to_dist_git import sg2dg
from sourcegit.cli.sourcegit_to_srpm import sg2srpm
from sourcegit.cli.watch_fedora_ci import watcher
from sourcegit.cli.watch_sg_pr import watch_pr
from sourcegit.config import Config, get_context_settings
from sourcegit.utils import set_logging

logger = logging.getLogger(__name__)


@click.group("sourcegit", context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True)
@click.option("--fas-user")
@click.option("-k", "--keytab")
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def sourcegit_base(ctx, **kwargs):
    ctx.obj = Config(**kwargs)
    if ctx.obj.debug:
        set_logging(level=logging.DEBUG)
        logger.debug("logging set to DEBUG")

    elif ctx.obj.verbose:
        set_logging(level=logging.INFO,
                    format="%(message)s")
        logger.debug("logging set to INFO")


@click.command("version")
def version():
    """Display the version."""
    click.echo(sourcegit.__version__)


sourcegit_base.add_command(sg2dg)
sourcegit_base.add_command(sg2srpm)
sourcegit_base.add_command(watcher)
sourcegit_base.add_command(version)
sourcegit_base.add_command(watch_pr)

if __name__ == '__main__':
    sourcegit_base()
