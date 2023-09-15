# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""Command to initialize a source-git repository"""

import logging
from typing import Optional

import click
import git

from packit.api import PackitAPI
from packit.cli.types import GitRepoParameter
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings
from packit.config.config import pass_config

logger = logging.getLogger(__name__)


@click.command("init", context_settings=get_context_settings())
@click.argument("upstream_ref")
@click.argument("source_git", type=GitRepoParameter(from_ref_param="upstream_ref"))
@click.argument("dist_git", type=GitRepoParameter())
@click.option(
    "--upstream-url",
    help="""Git URL of the upstream repository. It is saved
    in the source-git configuration if it is specified.""",
)
@click.option(
    "--upstream-remote",
    help="""Name of the remote pointing to the upstream repository.
    If --upstream-url is not specified, the fetch URL of this remote
    is saved in the source-git configuration as the Git URL of the
    upstream project. Defaults to 'origin'.""",
)
@click.option(
    "--pkg-tool",
    help="""Name or path of the packaging tool used to work
    with sources in the dist-git repo. A variant of 'rpkg'.
    Defaults to 'fedpkg' or the tool configured in the Packit
    configuration.""",
)
@click.option(
    "--pkg-name",
    help="""The name of the package in the distro.
    Defaults to the directory name of DIST_GIT.""",
)
@pass_config
@cover_packit_exception
def source_git_init(
    config,
    dist_git: git.Repo,
    source_git: git.Repo,
    upstream_ref: str,
    upstream_url: Optional[str],
    upstream_remote,
    pkg_tool: Optional[str],
    pkg_name: Optional[str],
):
    """Initialize SOURCE_GIT as a source-git repo by applying downstream
    patches from DIST_GIT as Git commits on top of UPSTREAM_REF.

    SOURCE_GIT needs to be an existing clone of the upstream repository.

    UPSTREAM_REF is a tag, branch or commit from SOURCE_GIT.

    SOURCE_GIT and DIST_GIT are paths to the source-git and dist-git
    repos. Branch names can be specified, separated by colons.

    If a branch name is specified for SOURCE_GIT, the branch is checked
    out and reset to UPSTREAM_REF.

    If a branch name is specified for DIST_GIT, the branch is checked
    out before setting up the source-git repo. This branch is expected
    to exist.

    Each Git commit created in SOURCE_GIT will have a 'From-dist-git-commit'
    trailer to mark the hash of the dist-git commit from which it is created.

    To learn more about source-git, please check

        https://packit.dev/docs/source-git/

    Examples:

    \b
        $ packit source-git init v2.3.1 src/acl:rawhide rpms/acl:rawhide
        $ packit source-git init --pkg-tool centpkg v2.3.1 src/acl rpms/acl
    """
    logger.warning(
        "Generating source-git repositories is experimental, "
        "please give us feedback if it does things differently than you expect.",
    )
    api = PackitAPI(config=config, package_config=None)
    api.init_source_git(
        dist_git=dist_git,
        source_git=source_git,
        upstream_ref=upstream_ref,
        upstream_url=upstream_url,
        upstream_remote=upstream_remote,
        pkg_tool=pkg_tool or config.pkg_tool,
        pkg_name=pkg_name,
    )
