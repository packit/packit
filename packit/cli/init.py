# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import get_context_settings
from packit.config.config import pass_config
from packit.constants import CONFIG_FILE_NAMES, PACKIT_CONFIG_TEMPLATE
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "-f", "--force", is_flag=True, help="Reset config to default if already exists."
)
@click.option(
    "--upstream-url",
    help="URL or local path to the upstream project; "
    "defaults to current git repository",
)
@click.option(
    "--upstream-ref",
    help="Use this upstream git ref as a base for your source-git repo; "
    "defaults to current tip of the git repository",
)
@click.option(
    "--fedora-package",
    help="Pick spec file from this Fedora Linux package; "
    "implies creating a source-git repo",
)
@click.option(
    "--centos-package",
    help="Pick spec file from this CentOS Linux or CentOS Stream package; "
    "implies creating a source-git repo",
)
@click.option(
    "--dist-git-branch",
    help="Get spec file from this downstream branch, "
    "for Fedora this defaults to master, for CentOS it's c8s. "
    "When --dist-git-path is set, the default is the branch which is already checked out.",
)
@click.option(
    "--dist-git-path",
    help="Path to the dist-git repo to use. If this is defined, "
    "--fedora-package and --centos-package are ignored.",
)
@pass_config
@cover_packit_exception
def init(
    config,
    path_or_url,
    force,
    upstream_url,
    upstream_ref,
    fedora_package,
    centos_package,
    dist_git_branch,
    dist_git_path: Optional[str],
):
    """
    Initiate a repository to start using packit.

    If you specify --upstream-url, then a source-git repository is made,
    otherwise only configuration file packit.yaml is created.

    To learn more about source-git, please check
    https://packit.dev/docs/source-git/
    """
    working_dir = path_or_url.working_dir
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

    if fedora_package or centos_package or dist_git_branch or dist_git_path:
        # we're doing a source-git repo
        logger.warning(
            "Generating source-git repositories is experimental, "
            "please give us feedback if it does things differently than you expect."
        )
        api = get_packit_api(
            config=config, local_project=path_or_url, load_packit_yaml=False
        )
        dg_path = Path(dist_git_path) if dist_git_path else None
        api.create_sourcegit_from_upstream(
            upstream_url=upstream_url,
            upstream_ref=upstream_ref,
            dist_git_path=dg_path,
            dist_git_branch=dist_git_branch,
            fedora_package=fedora_package,
            centos_package=centos_package,
        )
        return

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
