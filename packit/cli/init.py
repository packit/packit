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

"""
Generate initial configuration for packit
"""

import logging
import os
from pathlib import Path
from typing import Optional

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings
from packit.constants import CONFIG_FILE_NAMES, PACKIT_CONFIG_TEMPLATE
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "-f", "--force", is_flag=True, help="Reset config to default if already exists."
)
@cover_packit_exception
def init(path_or_url, force):
    """
    Generate new packit config.
    """

    working_dir = Path(path_or_url.working_dir)
    config_path = get_existing_config(working_dir)
    if config_path:
        if not force:
            raise PackitException(
                f"Packit config {config_path} already exists."
                " If you want to regenerate it use `packit init --force`"
            )
    else:
        # Use default name
        config_path = working_dir / ".packit.yaml"

    template_data = {
        "upstream_package_name": path_or_url.repo_name,
        "downstream_package_name": path_or_url.repo_name,
    }

    generate_config(
        config_file=config_path, write_to_file=True, template_data=template_data
    )


def get_existing_config(working_dir: Path) -> Optional[Path]:
    # find name of config file if already exists
    for config_file_name in CONFIG_FILE_NAMES:
        config_file_path = working_dir / config_file_name
        if config_file_path.is_file():
            return config_file_path
    return None


def generate_config(
    config_file: Path, write_to_file: bool = False, template_data: dict = None
) -> str:
    """
    Generate config file from provided data
    :param config_file: Path, .packit.yaml by default
    :param write_to_file: bool, write to config_file? False by default
    :param template_data: dict, example:
    {
        "upstream_package_name": "packitos",
        "downstream_package_name": "packit",
    }
    :return: str, generated config
    """
    output_config = PACKIT_CONFIG_TEMPLATE.format(
        downstream_package_name=template_data["downstream_package_name"],
        upstream_package_name=template_data["upstream_package_name"],
    )

    if write_to_file:
        config_file.write_text(output_config)
        logger.debug(f"Packit config file '{config_file}' changed.")

    return output_config
