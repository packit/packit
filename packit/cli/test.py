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


@click.command("test", context_settings=get_context_settings(), short_help="Run tmt tests locally")
# @pass_config
# @cover_packit_exception
# @iterate_packages
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="source build"),
)
@click.option(
    "--rpm_paths",
    multiple=True,
    help="Path(s) to RPMs that should be installed in the test environment."
)
@click.option(
    "--target",
    default="fedora-latest",
    help="Container/VM image to use."
)
@click.option(
    "--context",
    help="Comment for the build test",
    default="initiator=packit",
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
@iterate_packages
def test(
    config,
    package_config,
    target,
    context,
    rpm_paths,
    path_or_url,
):
    """
    Run tmt tests locally without needing a PR or release
    """
    print("got inside test command")
    logger.debug("got inside test command")
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    cmd_result_stdout = api.run_local_test(
        chroot=target,
        context=context,
        rpm_paths=rpm_paths,
    )

    if cmd_result_stdout:
        # TODO : What to do with response from tmt
        sys.exit(0)
    sys.exit(1)
