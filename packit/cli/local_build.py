# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings

logger = logging.getLogger("packit")


@click.command("local-build", context_settings=get_context_settings())
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@pass_config
@cover_packit_exception
def local_build(config, path_or_url, upstream_ref):
    """
    Create RPMs using content of the upstream repository.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    rpm_paths = api.create_rpms(upstream_ref=upstream_ref)
    logger.info("RPMs:")
    for path in rpm_paths:
        logger.info(f" * {path}")
