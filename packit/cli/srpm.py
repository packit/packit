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


@click.command("srpm", context_settings=get_context_settings())
@click.option(
    "--output",
    metavar="FILE",
    help="Write the SRPM to FILE instead of current dir.",
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--update-release/--no-update-release",
    default=None,
    help=(
        "Specifies whether to update Release. "
        "Defaults to value set in configuration, which defaults to yes."
    ),
)
@click.option(
    "--bump/--no-bump",
    default=None,
    help="Deprecated. Use --[no-]update-release instead.",
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
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="source build"),
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@pass_config
@cover_packit_exception
@iterate_packages
def srpm(
    config,
    output,
    path_or_url,
    upstream_ref,
    update_release,
    bump,
    release_suffix,
    default_release_suffix,
    package_config,
):
    """
    Create new SRPM (.src.rpm file) using content of the upstream repository.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )
    if bump is not None:
        if update_release is not None:
            raise click.UsageError(
                "--[no-]bump and --[no-]update-release are mutually exclusive",
            )
        logger.warning("--[no-]bump is deprecated. Use --[no-]update-release instead.")
        update_release = bump
    release_suffix = ChangelogHelper.resolve_release_suffix(
        api.package_config,
        release_suffix,
        default_release_suffix,
    )

    srpm_path = api.create_srpm(
        output_file=output,
        upstream_ref=upstream_ref,
        update_release=update_release,
        release_suffix=release_suffix,
    )
    logger.info(f"SRPM: {srpm_path}")
