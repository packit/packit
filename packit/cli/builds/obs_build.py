# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os.path
from tempfile import TemporaryDirectory
from typing import Optional

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import get_context_settings, pass_config
from packit.config.config import Config
from packit.config.package_config import PackageConfig
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)
from packit.utils import obs_helper

logger = logging.getLogger(__name__)


@click.command("in-obs", context_settings=get_context_settings())
@click.option(
    "--owner",
    help="OBS user, owner of the project. (defaults to the username from the oscrc)",
)
@click.option(
    "--project",
    help="Project name to build in. It will be created if does not exist."
    " It defaults to home:$owner:packit:$pkg",
)
@click.option(
    "--targets",
    help="Comma separated list of chroots to build in. (defaults to 'fedora-rawhide-x86_64')",
    default="fedora-rawhide-x86_64",
)
@click.option(
    "--description",
    help="Description of the project to build in.",
    default=None,
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option("--wait/--no-wait", default=True, help="Wait for the build to finish")
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="build"),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
@iterate_packages
def obs(
    config: Config,
    owner: Optional[str],
    project: str,
    targets: str,
    description: Optional[str],
    upstream_ref: Optional[str],
    wait: bool,
    package_config: PackageConfig,
    path_or_url,
) -> None:
    """
    Build selected project in OBS

    Before Running this command, your opensuse user account and password needs to be
    configured in osc configuration file ~/.config/osc/oscrc. This can be done by running `osc`.
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    project_name, package_name = obs_helper.create_obs_project(
        owner=owner,
        package_config=package_config,
        project=project,
        targets=targets,
        description=description,
    )

    with TemporaryDirectory() as tmp_dir:
        api.run_obs_build(
            build_dir=tmp_dir,
            package_name=package_name,
            project_name=project_name,
            wait=wait,
            upstream_ref=upstream_ref,
        )
