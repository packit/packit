import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings

logger = logging.getLogger("packit")


@click.command("srpm", context_settings=get_context_settings())
@click.option(
    "--output", metavar="FILE", help="Write the SRPM to FILE instead of current dir."
)
@click.argument(
    "path_or_url", type=LocalProjectParameter(), default=os.path.abspath(os.path.curdir)
)
@pass_config
@cover_packit_exception
def srpm(config, output, path_or_url):
    """
    Create new SRPM (.src.rpm file) using content of the upstream repository.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    srpm_path = api.create_srpm(output_file=output)
    logger.info("SRPM: %s", srpm_path)
