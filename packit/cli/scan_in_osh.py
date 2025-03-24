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


@click.command("scan-in-osh", context_settings=get_context_settings())
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
    "--base-srpm",
    help="Base SRPM to perform a differential build against",
    default=None,
)
@click.option(
    "--base-nvr",
    help="Base NVR in Koji to perform a differential build against",
    default=None,
)
@click.option(
    "--comment",
    help="Comment for the build",
    default="Submitted through Packit.",
)
@click.option(
    "--csmock-args",
    help="Pass additional arguments to csmock",
    default=None,
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
def scan_in_osh(
    config,
    path_or_url,
    package_config,
    target,
    base_srpm,
    base_nvr,
    comment,
    csmock_args,
):
    """
    Perform a scan through OpenScanHub.
    You need a valid Kerberos ticket and set `dns_canonicalize_hostname=false`
    in Kerberos configurations.
    Documentation can be found at https://fedoraproject.org/wiki/OpenScanHub.
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    if base_srpm:
        logger.debug(f"Base SRPM: {base_srpm}")

    cmd_result_stdout = api.run_osh_build(
        chroot=target,
        base_srpm=base_srpm,
        base_nvr=base_nvr,
        comment=comment,
        csmock_args=csmock_args,
    )

    if cmd_result_stdout:
        build_url = json.loads(cmd_result_stdout)["url"]
        logger.info(f"Scan URL: {build_url}")
        sys.exit(0)

    sys.exit(1)
