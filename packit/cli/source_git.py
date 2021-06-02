# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""The 'source-git' subcommand for Packit"""

import click

from packit.cli.update_dist_git import update_dist_git


@click.group("source-git")
def source_git():
    """Subcommand to collect source-git related functionality"""
    pass


source_git.add_command(update_dist_git)
