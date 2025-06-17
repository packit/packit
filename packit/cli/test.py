# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
import os
import sys

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import (
    get_context_settings,
    pass_config,
)
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)

logger = logging.getLogger(__name__)


@click.command("test", context_settings=get_context_settings())
@pass_config
@cover_packit_exception
@iterate_packages
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="build"),
)
@click.option(
    "--target",
    help="Chroot to build in. (defaults to 'fedora-rawhide-x86_64')",
    default="fedora-rawhide-x86_64",
)
@click.option(
    "--context",
    help="Comment for the build test",
    default="initiator=packit",
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
def test(
    config,
    package_config,
    target,
    context,
):
    """
    Run tmt tests locally without needing a PR or release
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
    )

    cmd_result_stdout = api.run_osh_build(
        chroot=target,
        comment=context,
    )

    if cmd_result_stdout:
        build_url = json.loads(cmd_result_stdout)["url"]
        logger.info(f"Scan URL: {build_url}")
        sys.exit(0)

    sys.exit(1)
