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
from os import getcwd
from pathlib import Path

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings
from packit.constants import CONFIG_FILE_NAMES, PACKIT_CONFIG_TEMPLATE
from packit.exceptions import PackitException

logger = logging.getLogger(__file__)


@click.command("generate", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=getcwd())
@click.option(
    "-f", "--force", is_flag=True, help="Reset config to default if already exists."
)
@cover_packit_exception
def generate(path_or_url, force):
    """
    Generate new packit config.
    """

    # find name of config file if already exists
    config_file_name = None
    for existing_config_file in CONFIG_FILE_NAMES:
        if (Path.cwd() / existing_config_file).is_file():
            config_file_name = existing_config_file
            if not force:
                raise PackitException(
                    f"Packit config {config_file_name} already exists."
                    " If you want to regenerate it use `packit generate --force`"
                )
            break

    template_data = {
        "upstream_project_name": path_or_url.repo_name,
        "downstream_package_name": path_or_url.repo_name,
    }

    generate_config(
        write_to_file=True,
        template_data=template_data,
        config_file_name=config_file_name,
    )


def generate_config(write_to_file=False, template_data=None, config_file_name=None):
    """
    Generate config file from provided data
    :param write_to_file: bool, False by default
    :param template_data: dict, example:
    {
        "upstream_project_name": "packitos",
        "downstream_package_name": "packit",
    }
    :param config_file_name: str, name of config file, `.packit.yaml` by default
    :return: str, generated config
    """
    # default name
    config_file_name = config_file_name or ".packit.yaml"

    output_config = PACKIT_CONFIG_TEMPLATE.format(
        downstream_package_name=template_data["downstream_package_name"],
        upstream_project_name=template_data["upstream_project_name"],
    )

    if write_to_file:
        Path(config_file_name).write_text(output_config)

    return output_config
