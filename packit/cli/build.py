# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""The 'build' subcommand for Packit"""

import logging

import click

from packit.cli.builds.copr_build import copr
from packit.cli.builds.koji_build import koji
from packit.cli.builds.local_build import local
from packit.cli.builds.mock_build import mock
from packit.cli.builds.in_image_builder import in_image_builder

logger = logging.getLogger(__name__)


@click.group("build")
@click.option(
    "--srpm",
    help="Build the SRPM from FILE instead of implicit SRPM build.",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@click.pass_context
def build(ctx, srpm):
    """Subcommand to collect build related functionality"""
    ctx.obj.srpm_path = srpm


build.add_command(copr)
build.add_command(koji)
build.add_command(local)
build.add_command(mock)
build.add_command(in_image_builder)
