# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""Command to initialize a source-git repository"""

import logging
import os
import pathlib
from typing import Optional

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import get_packit_api
from packit.config.config import pass_config
from packit.config import get_context_settings
from packit.exceptions import PackitNotAGitRepoException

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@click.option(
    "--upstream-url",
    help="URL or local path to the upstream project; "
    "defaults to current git repository",
)
@click.option(
    "--upstream-ref",
    help="Use this upstream git ref as a base for your source-git repo; "
    "defaults to current tip of the git repository",
)
@click.option(
    "--fedora-package",
    help="Pick spec file from this Fedora Linux package; "
    "implies creating a source-git repo",
)
@click.option(
    "--centos-package",
    help="Pick spec file from this CentOS Linux or CentOS Stream package; "
    "implies creating a source-git repo",
)
@click.option(
    "--dist-git-branch",
    help="Get spec file from this downstream branch, "
    "for Fedora this defaults to main, for CentOS it's c9s. "
    "When --dist-git-path is set, the default is the branch which is already checked out.",
)
@click.option(
    "--dist-git-path",
    help="Path to the dist-git repo to use. If this is defined, "
    "--fedora-package and --centos-package are ignored.",
)
@pass_config
def source_git_init(
    config,
    path_or_url,
    upstream_url,
    upstream_ref,
    fedora_package,
    centos_package,
    dist_git_branch,
    dist_git_path: Optional[str],
):
    """Initialize a source-git repository

    To learn more about source-git, please check

        https://packit.dev/docs/source-git/
    """
    logger.warning(
        "Generating source-git repositories is experimental, "
        "please give us feedback if it does things differently than you expect."
    )
    try:
        api = get_packit_api(
            config=config, local_project=path_or_url, load_packit_yaml=False
        )
    except PackitNotAGitRepoException:
        logger.error(
            "The init command is expected to be run in a git repository. "
            "Current branch in the repo will be turned into a source-git repo. "
            "We suggest to run the command "
            "in a blank git repository or in a new branch of the upstream project."
        )
        raise
    dg_path = pathlib.Path(dist_git_path) if dist_git_path else None
    api.create_sourcegit_from_upstream(
        upstream_url=upstream_url,
        upstream_ref=upstream_ref,
        dist_git_path=dg_path,
        dist_git_branch=dist_git_branch,
        fedora_package=fedora_package,
        centos_package=centos_package,
    )
