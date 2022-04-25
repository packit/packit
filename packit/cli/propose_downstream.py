# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Update selected component from upstream in Fedora
"""

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings, PackageConfig
from packit.config.aliases import get_branches

logger = logging.getLogger(__name__)


def get_dg_branches(api, dist_git_branch):
    cmdline_dg_branches = dist_git_branch.split(",") if dist_git_branch else []
    config_dg_branches = []
    if isinstance(api.package_config, PackageConfig):
        config_dg_branches = (
            api.package_config.get_propose_downstream_dg_branches_value()
        )

    default_dg_branch = api.dg.local_project.git_project.default_branch

    dg_branches = (
        cmdline_dg_branches or config_dg_branches or default_dg_branch.split(",")
    )

    return get_branches(*dg_branches, default_dg_branch=default_dg_branch)


@click.command("propose-downstream", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Comma separated list of target branches in dist-git to release into. "
    "(defaults to all branches)",
)
@click.option(
    "--dist-git-path",
    help="Path to dist-git repo to work in. "
    "Otherwise clone the repo in a temporary directory.",
)
@click.option(
    "--local-content",
    is_flag=True,
    default=False,
    help="Do not checkout release tag. Use the current state of the repo. "
    "This option is set by default for source-git repos",
)
@click.option(
    "--force-new-sources",
    is_flag=True,
    default=False,
    help="Upload the new sources also when the archive is already in the lookaside cache.",
)
@click.option(
    "--pr/--no-pr",
    default=None,
    help=(
        "Create a pull request to downstream repository or push directly. "
        "If not set, defaults to value set in configuration."
    ),
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--force",
    "-f",
    default=False,
    is_flag=True,
    help="Don't discard changes in the git repo by default, unless this is set.",
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@click.argument("version", required=False)
@pass_config
@cover_packit_exception
def propose_downstream(
    config,
    dist_git_path,
    dist_git_branch,
    force_new_sources,
    pr,
    local_content,
    path_or_url,
    upstream_ref,
    version,
    force,
):
    """
    Land a new upstream release in Fedora.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """

    api = get_packit_api(
        config=config, dist_git_path=dist_git_path, local_project=path_or_url
    )
    if pr is None:
        pr = api.package_config.create_pr

    branches_to_update = get_dg_branches(api, dist_git_branch)

    click.echo(
        f"Proposing update of the following branches: {', '.join(branches_to_update)}"
    )

    for branch in branches_to_update:
        api.sync_release(
            dist_git_branch=branch,
            use_local_content=local_content,
            version=version,
            force_new_sources=force_new_sources,
            upstream_ref=upstream_ref,
            create_pr=pr,
            force=force,
        )
