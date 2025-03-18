# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from importlib.metadata import version

import click

from packit.cli.build import build
from packit.cli.config import config
from packit.cli.create_update import create_update
from packit.cli.dist_git import dist_git
from packit.cli.init import init
from packit.cli.prepare_sources import prepare_sources
from packit.cli.propose_downstream import propose_downstream, pull_from_upstream
from packit.cli.push_updates import push_updates
from packit.cli.scan_in_osh import scan_in_osh
from packit.cli.source_git import source_git
from packit.cli.srpm import srpm
from packit.cli.status import status
from packit.cli.sync_from_downstream import sync_from_downstream
from packit.cli.validate_config import validate_config
from packit.config import Config, get_context_settings
from packit.utils.logging import set_logging

logger = logging.getLogger("packit")


@click.group("packit", context_settings=get_context_settings())
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
@click.version_option(version=version("packitos"), message="%(version)s")
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
    else:
        set_logging(level=logging.INFO)

    packit_version = version("packitos")
    logger.debug(f"Packit {packit_version} is being used.")


packit_base.add_command(propose_downstream)
packit_base.add_command(pull_from_upstream)
packit_base.add_command(sync_from_downstream)
packit_base.add_command(build)
packit_base.add_command(create_update)
packit_base.add_command(push_updates)
packit_base.add_command(srpm)
packit_base.add_command(status)
packit_base.add_command(init)
packit_base.add_command(validate_config)
packit_base.add_command(source_git)
packit_base.add_command(prepare_sources)
packit_base.add_command(dist_git)
packit_base.add_command(scan_in_osh)
packit_base.add_command(config)

if __name__ == "__main__":
    packit_base()
