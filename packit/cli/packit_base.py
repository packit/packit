# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

import click
from pkg_resources import get_distribution

from packit.cli.build import build
from packit.cli.copr_build import copr_build
from packit.cli.create_update import create_update
from packit.cli.init import init
from packit.cli.local_build import local_build
from packit.cli.push_updates import push_updates
from packit.cli.srpm import srpm
from packit.cli.status import status
from packit.cli.sync_from_downstream import sync_from_downstream
from packit.cli.update import update
from packit.config import Config, get_context_settings
from packit.utils import set_logging

logger = logging.getLogger("packit")


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        if cmd_name == "generate":
            click.secho(
                "WARNING: 'packit generate' is deprecated and it "
                "is going to be removed. Use 'packit init' instead.",
                fg="yellow",
            )
            return click.Group.get_command(self, ctx, "init")
        else:
            return click.Group.get_command(self, ctx, cmd_name)


@click.group("packit", cls=AliasedGroup, context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True, help="Enable debug logs.")
@click.option("--fas-user", help="Fedora Account System username.")
@click.option("-k", "--keytab", help="Path to FAS keytab file.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Do not perform any remote changes (pull requests or comments).",
)
@click.version_option(
    version=get_distribution("packitos").version, message="%(version)s"
)
@click.pass_context
def packit_base(ctx, debug, fas_user, keytab, dry_run):
    """Integrate upstream open source projects into Fedora operating system."""
    if debug:
        # to be able to logger.debug() also in get_user_config()
        set_logging(level=logging.DEBUG)

    c = Config.get_user_config()
    c.debug = debug or c.debug
    c.dry_run = dry_run or c.dry_run
    c.fas_user = fas_user or c.fas_user
    c.keytab_path = keytab or c.keytab_path
    ctx.obj = c

    if ctx.obj.debug:
        set_logging(level=logging.DEBUG)
        set_logging(logger_name="sandcastle", level=logging.DEBUG)
    else:
        set_logging(level=logging.INFO)

    packit_version = get_distribution("packitos").version
    logger.debug(f"Packit {packit_version} is being used.")


packit_base.add_command(update)
packit_base.add_command(sync_from_downstream)
packit_base.add_command(build)
packit_base.add_command(copr_build)
packit_base.add_command(create_update)
packit_base.add_command(push_updates)
packit_base.add_command(srpm)
packit_base.add_command(status)
packit_base.add_command(init)
packit_base.add_command(local_build)

if __name__ == "__main__":
    packit_base()
