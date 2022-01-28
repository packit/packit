# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import logging
import os
from pathlib import Path

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.schema import JobConfigSchema

logger = logging.getLogger("packit")


def load_job_config(job_config):
    if job_config:
        try:
            return JobConfigSchema().loads(job_config)
        except Exception as ex:
            logger.error(f"Loading of JobConfig wasn't successful: {ex}")
    return None


@click.command("prepare-sources", context_settings=get_context_settings())
@click.option(
    "--result-dir",
    metavar="DIR",
    help="Copy the sources into DIR. By default, `prepare_sources_result` directory "
    "in the current working directory is created.",
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--bump/--no-bump",
    default=True,
    help="Specifies whether to bump version or not.",
)
@click.option(
    "--release-suffix",
    default=None,
    type=click.STRING,
    help="Specifies release suffix. Allows to override default generated:"
    "{current_time}.{sanitized_current_branch}{git_desc_suffix}",
)
@click.option(
    "--job-config",
    default=None,
    type=click.STRING,
    help="Internal option to override package config found in the repository "
    "(needed for packit service).",
)
@click.option(
    "--ref",
    default="",
    type=click.STRING,
    help="Git reference to checkout.",
)
@click.option(
    "--pr-id",
    default=None,
    type=click.STRING,
    help="Specifies PR to checkout.",
)
@click.option(
    "--merge-pr/--no-merge-pr",
    is_flag=True,
    default=True,
    help="Specifies whether to merge PR into the base branch in case pr-id is specified.",
)
@click.option(
    "--target-branch",
    default=None,
    type=click.STRING,
    help="Specifies target branch which PR should be merged into.",
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(
        ref_param_name="ref",
        pr_id_param_name="pr_id",
        merge_pr_param_name="merge_pr",
        target_branch_param_name="target_branch",
    ),
    default=os.path.curdir,
)
@pass_config
@cover_packit_exception
def prepare_sources(
    config,
    path_or_url,
    job_config,
    upstream_ref,
    bump,
    release_suffix,
    result_dir,
    ref,
    pr_id,
    merge_pr,
    target_branch,
):
    """
    Prepare sources for a new SRPM build using content of the upstream repository.
    Determine version, create an archive or download upstream and create patches for sourcegit,
    fix/update the specfile to use the right archive, download the remote sources.
    Behaviour can be customized by specifying actions (post-upstream-clone, get-current-version,
    create-archive, create-patches, fix-spec-file) in the configuration.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    job_config = load_job_config(job_config)

    if not result_dir:
        result_dir = Path.cwd().joinpath("prepare_sources_result")
        logger.debug(f"Setting result_dir to the default one: {result_dir}")

    api = get_packit_api(
        config=config, local_project=path_or_url, job_config=job_config
    )

    api.prepare_sources(
        upstream_ref=upstream_ref,
        bump_version=bump,
        release_suffix=release_suffix,
        result_dir=result_dir,
    )
