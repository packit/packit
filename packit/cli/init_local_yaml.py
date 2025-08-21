# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import click

from packit.config import (
    get_context_settings,
    pass_config,
)

logger = logging.getLogger(__name__)


@click.command(
    "init-local-config",
    context_settings=get_context_settings(),
    short_help="Creates a localyaml config file for and ensures it's not version controlled",
)
@pass_config
def init_local_yaml(config):
    """Initialize packit-local yaml configuration file."""
    config_path = Path(".packitLocal.yaml")

    if config_path.exists() and not click.confirm(
        f"{config_path} already exists. Overwrite?",
    ):
        return

    template = """
        # Packit local configuration (not version controlled)
        # This file overrides user and system configuration for this project only

        # Authentication (optional - overrides ~/.config/packit.yaml)
        # authentication:
        #   github.com:
        #     token: YOUR_TOKEN
    """

    config_path.write_text(template)
    click.echo(f"Created {config_path}")

    # Add packit local to .gitignore
    ensure_gitignore_entry()


def ensure_gitignore_entry():
    """Ensure .packitLocal.yaml is in .gitignore."""
    gitignore_path = Path(".gitignore")
    localYamlFile = ".packitLocal.yaml"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if localYamlFile not in content:
            with open(gitignore_path, "a") as f:
                f.write(
                    f"\n# Packit local config (local only overrides)\n{localYamlFile}\n",
                )
            click.echo(f"Added {localYamlFile} to .gitignore")
    else:
        with open(gitignore_path, "w") as f:
            f.write(f"# Packit local config (local only overrides)\n{localYamlFile}\n")
        click.echo(f"Created .gitignore with {localYamlFile}")
