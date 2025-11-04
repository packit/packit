# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import sys

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import (
    cover_packit_exception,
    get_packit_api,
    iterate_packages,
)
from packit.config import (
    get_context_settings,
    pass_config,
)
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)
from packit.utils.local_test_utils import LocalTestUtils

logger = logging.getLogger(__name__)


@click.command(
    "test",
    context_settings=get_context_settings(),
    help="""
        Run tmt tests locally using content from the upstream repository.

        This command builds RPMs from the current repository state and runs
        tests in containerized environments, mimicking Packit's testing service
        behavior for local debugging and development.
    """,
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
    help=(
        "Path to RPM file(s) to test. Can be used multiple times."
        "If not provided, RPMs will be built automatically from source."
    ),
)
@click.option(
    "--target",
    default="fedora:rawhide",
    help=(
        "Container image for the testing environment, "
        "e.g., `fedora:39`, `centos:stream9`."
    ),
)
@click.option(
    "--plans",
    multiple=True,
    help=(
        "List of specific tmt plans to run. Can be used multiple times. "
        "If not specified, all plans are executed."
    ),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "--clean-before/--no-clean-before",
    default=False,
    help="Run 'tmt clean --all' before starting the test (default: disabled).",
)
@pass_config
@cover_packit_exception
@iterate_packages
def test(
    config,
    package_config,
    target,
    rpm_paths,
    path_or_url,
    plans,
    clean_before,
):
    """
    Run tmt tests locally without needing a PR or release
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    # TODO: Expose options for mock build as CLI flags instead of using hardcoded values.
    tmt_output = api.run_local_test(
        target=target,
        rpm_paths=rpm_paths,
        plans=plans,
        release_suffix=None,
        default_release_suffix=False,
        upstream_ref=None,
        srpm_dir=api.up.local_project.working_dir,
        default_mock_resultdir=True,
        resultdir=".",
        root=None,
        clean_before=clean_before,
    )

    if not tmt_output:
        sys.exit(1)

    no_of_executed_tests, no_of_passed_tests = LocalTestUtils.parse_tmt_response(
        tmt_output,
    )
    if no_of_executed_tests == no_of_passed_tests:
        logger.info(f"All {no_of_passed_tests} test(s) passed.")
        sys.exit(0)

    logger.error("Error! Some tests failed.")
    logger.error("--- tmt stdout ---")
    logger.error(tmt_output)
    sys.exit(1)
