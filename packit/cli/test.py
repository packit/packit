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
logger = logging.getLogger(__name__)


@click.command("test", context_settings=get_context_settings(), short_help="Run tmt tests locally")
@cover_packit_exception
@iterate_packages
@click.option(
    "--rpm_paths",
    multiple=True,
    help="Path(s) to RPMs that should be installed in the test environment."
)
@click.option(
    "--chroot",
    default="fedora-latest",
    help="Container/VM image to use (same syntax as --target elsewhere)."
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
    rpm_paths
):
    """
    Run tmt tests locally without needing a PR or release
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
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
