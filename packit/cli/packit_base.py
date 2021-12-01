# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
from packit.cli.prepare_sources import prepare_sources
from packit.cli.propose_downstream import propose_downstream
from packit.cli.validate_config import validate_config
from packit.cli.source_git import source_git
from packit.config import Config, get_context_settings
from packit.utils.logging import set_logging

logger = logging.getLogger("packit")


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        if cmd_name == "propose-update":
            click.secho(
                "WARNING: 'packit propose-update' is deprecated and will be removed. "
                "Use 'packit propose-downstream' instead.",
                fg="yellow",
            )
            return click.Group.get_command(self, ctx, "propose-downstream")
        else:
            return click.Group.get_command(self, ctx, cmd_name)


@click.group("packit", cls=AliasedGroup, context_settings=get_context_settings())
@click.option("-d", "--debug", is_flag=True, help="Enable debug logs.")
@click.option("--fas-user", help="Fedora Account System username.")
@click.option("-k", "--keytab", help="Path to FAS keytab file.")
@click.option(
    "--remote",
    default=None,
    help=(
        "Name of the remote to discover upstream project URL, "
        "If this is not specified, default to the first remote."
    ),
)
@click.option(
    "-c",
    "--config",
    "package_config_path",
    help="Path to package configuration file (defaults to .packit.yaml or packit.yaml)",
)
@click.version_option(
    version=get_distribution("packitos").version, message="%(version)s"
)
@click.pass_context
def packit_base(ctx, debug, fas_user, keytab, remote, package_config_path):
    """Integrate upstream open source projects into Fedora operating system."""
    if debug:
        # to be able to logger.debug() also in get_user_config()
        set_logging(level=logging.DEBUG)

    c = Config.get_user_config()
    c.debug = debug or c.debug
    c.fas_user = fas_user or c.fas_user
    c.keytab_path = keytab or c.keytab_path
    c.upstream_git_remote = remote or c.upstream_git_remote
    c.package_config_path = package_config_path or c.package_config_path
    ctx.obj = c

    if ctx.obj.debug:
        set_logging(level=logging.DEBUG)
        set_logging(logger_name="sandcastle", level=logging.DEBUG)
        set_logging(logger_name="rebasehelper", level=logging.DEBUG)
    else:
        set_logging(level=logging.INFO)
        # rebase-helper prints errors about missing patches which are not an error in our case
        #   Patch glibc-fedora-nscd.patch does not exist
        set_logging(logger_name="rebasehelper", level=logging.CRITICAL)

    packit_version = get_distribution("packitos").version
    logger.debug(f"Packit {packit_version} is being used.")


packit_base.add_command(propose_downstream)
packit_base.add_command(sync_from_downstream)
packit_base.add_command(build)
packit_base.add_command(copr_build)
packit_base.add_command(create_update)
packit_base.add_command(push_updates)
packit_base.add_command(srpm)
packit_base.add_command(status)
packit_base.add_command(init)
packit_base.add_command(local_build)
packit_base.add_command(validate_config)
packit_base.add_command(source_git)
packit_base.add_command(prepare_sources)

if __name__ == "__main__":
    packit_base()
