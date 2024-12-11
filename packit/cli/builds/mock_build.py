# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import get_context_settings, pass_config
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)
from packit.utils.changelog_helper import ChangelogHelper

logger = logging.getLogger("packit")


@click.command("in-mock", context_settings=get_context_settings())
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--release-suffix",
    default=None,
    type=click.STRING,
    help="Specifies release suffix. Allows to override default generated:"
    "{current_time}.{sanitized_current_branch}{git_desc_suffix}",
)
@click.option(
    "--default-release-suffix",
    default=False,
    is_flag=True,
    help=(
        "Allows to use default, packit-generated, release suffix when some "
        "release_suffix is specified in the configuration."
    ),
)
@click.option(
    "-r",
    "--root",
    default="default",
    help=(
        "Uses specified chroot configuration. If ends with '.cfg', then it is "
        "treated as full path to the mock configuration."
    ),
)
@click.option(
    "--resultdir",
    default=None,
    type=click.Path(file_okay=False),
    help="Specifies the resultdir option for ‹mock› command, for details see mock(1)",
)
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="build"),
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@pass_config
@cover_packit_exception
@iterate_packages
def mock(
    config,
    upstream_ref,
    release_suffix,
    default_release_suffix,
    root,
    resultdir,
    package_config,
    path_or_url,
):
    """
    Build RPMs in mock using content of the upstream repository.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory.
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )
    release_suffix = ChangelogHelper.resolve_release_suffix(
        api.package_config,
        release_suffix,
        default_release_suffix,
    )

    if not config.srpm_path:
        config.srpm_path = api.create_srpm(
            upstream_ref=upstream_ref,
            srpm_dir=api.up.local_project.working_dir,
            release_suffix=release_suffix,
        )

    rpm_paths = api.run_mock_build(
        root=root,
        srpm_path=config.srpm_path,
        resultdir=resultdir,
    )
    logger.info("RPMs:")
    for path in rpm_paths:
        logger.info(f" * {path}")
