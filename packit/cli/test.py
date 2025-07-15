# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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


@click.command(
    "test",
    context_settings=get_context_settings(),
    short_help="Run tmt tests locally",
)
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="source build"),
)
@click.option(
    "--rpm_paths",
    multiple=True,
    help="Path(s) to RPMs that should be installed in the test environment.",
)
@click.option("--target", default="fedora:rawhide", help="Container/VM image to use.")
@click.option("--run-all", is_flag=True, help="flag to run all discovered test plans.")
@click.option("--plans", multiple=True, help="List of specific tmt plans to run.")
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
@iterate_packages
def test(
    config,
    package_config,
    target,
    rpm_paths,
    path_or_url,
    run_all,
    plans,
):
    """
    Run tmt tests locally without needing a PR or release
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    stdout = api.run_local_test(
        target=target,
        rpm_paths=rpm_paths,
        run_all=run_all,
        plans=plans,
    )

    if stdout:
        no_of_executed_tests, no_of_passed_tests = api.parse_tmt_response(
            stdout,
        )
        if no_of_executed_tests == no_of_passed_tests and no_of_executed_tests > 0:
            logger.info(f"✅ All {no_of_passed_tests} tests passed.")
            sys.exit(0)
        else:
            logger.error("Error! ❌ Some tests failed.")
            logger.error("--- tmt stdout ---")
            logger.error(stdout)
            sys.exit(1)
    sys.exit(1)
