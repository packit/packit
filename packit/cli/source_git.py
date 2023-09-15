# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""The 'source-git' subcommand for Packit"""

import click

from packit.cli.source_git_init import source_git_init
from packit.cli.source_git_status import source_git_status
from packit.cli.update_dist_git import update_dist_git
from packit.cli.update_source_git import update_source_git


@click.group("source-git")
def source_git():
    """Subcommand to collect source-git related functionality"""


source_git.add_command(update_dist_git)
source_git.add_command(update_source_git)
source_git.add_command(source_git_init)
source_git.add_command(source_git_status)
