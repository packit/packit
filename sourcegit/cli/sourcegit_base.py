import logging
import sys

import click

import sourcegit
from sourcegit.cli.sourcegit_to_dist_git import sg2dg
from sourcegit.cli.sourcegit_to_srpm import sg2srpm
from sourcegit.cli.watch_fedora_ci import main as watch_fedora_ci_main
from sourcegit.config import Config, get_context_settings
from sourcegit.utils import set_logging


@click.group("sourcegit", context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True)
@click.option("--fas-user")
@click.option("-k", "--keytab")
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def sourcegit_base(ctx, **kwargs):
    ctx.obj = Config(**kwargs)
    if ctx.obj.verbose:
        set_logging(level=logging.INFO,
                    format="%(message)s")

    if ctx.obj.debug:
        set_logging(level=logging.DEBUG)


@click.command("version")
def version():
    """Display the version."""
    click.echo(sourcegit.__version__)


@click.command("watch-fedora-ci")
def watch_fedora_ci():
    """Watch for flags on PRs: try to process those which we know mapping for."""
    ret_code = watch_fedora_ci_main()
    sys.exit(ret_code)


sourcegit_base.add_command(sg2dg)
sourcegit_base.add_command(sg2srpm)
sourcegit_base.add_command(watch_fedora_ci)
sourcegit_base.add_command(version)

if __name__ == '__main__':
    sourcegit_base()
