# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import time
from os import getcwd

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, JobType

logger = logging.getLogger("packit")


@click.command("in-image-builder")
@click.option(
    "--job-config-index",
    default=None,
    type=click.INT,
    help="Use N-th job definition to load configuration for the image build. "
    "The type needs to be vm_image_build.",
)
@click.option("--wait/--no-wait", default=False, help="Wait for the build to finish")
@click.argument("image_name", default=None, type=click.STRING)
@click.argument("path_or_url", type=LocalProjectParameter(), default=getcwd())
@pass_config
@cover_packit_exception
def in_image_builder(
    config,
    wait,
    image_name,
    job_config_index,
    path_or_url,
):
    """
    Create a VM image in Image Builder.

    ### EXPERIMENTAL ###

    This command is experimental and the integration with Image Builder will be
    changed in a backwards incompatible way in the future.

    Packit loads image build configuration from your packit.yaml file.

    When `--job-config-index` is not specified, the job configuration is loaded from your
    .packit.yaml and the first matching vm_image_build job is used.

    IMAGE_NAME is the name of the image to be created. Please pick something unique so it's
    easy to identify for you in the Image Builder interface and can be well associated
    with the image content.

    [PATH_OR_URL] argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config,
        local_project=path_or_url,
        job_config_index=job_config_index,
        job_type=JobType.vm_image_build,
    )

    build_id = api.submit_vm_image_build(
        image_distribution=api.package_config.image_distribution,
        image_name=image_name,
        image_request=api.package_config.image_request,
        image_customizations=api.package_config.image_customizations,
        copr_namespace=api.package_config.owner,
        copr_project=api.package_config.project,
        copr_chroot=api.package_config.copr_chroot,
    )
    logger.info(f"Image Build ID: {build_id}")
    logger.info("Browse in: https://console.redhat.com/insights/image-builder")

    if not wait:
        return 0
    logger.info(f"Getting status for build {build_id}.")
    while True:
        status = api.get_vm_image_build_status(build_id)
        if status not in ("building", "pending"):
            break
        logger.info(f"Status: {status}")
        time.sleep(5.0)

    # IB offers this link:
    # https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#LaunchInstanceWizard:ami=ami-08ee0689a0547e7ea
    # we could construct & print it too
