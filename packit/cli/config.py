# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import click

from packit.cli.validate_config import validate_config


@click.group()
def config():
    """Configuration-related commands."""


# Add the validate subcommand to the config group.
config.add_command(validate_config, name="validate")
