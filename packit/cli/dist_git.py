# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""The 'dist-git' subcommand for Packit"""

import click

from packit.cli.dist_git_init import init


@click.group("dist-git")
def dist_git():
    """Subcommand to collect dist-git related functionality"""


dist_git.add_command(init)
