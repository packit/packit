# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Update selected component from upstream in Fedora
"""

import functools
import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import PackageConfig, get_context_settings, pass_config
from packit.config.aliases import get_branches, get_fast_forward_merge_branches_for
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)

logger = logging.getLogger(__name__)


def get_dist_git_branches(api, dist_git_branch, pull_from_upstream=False):
    cmdline_dg_branches = dist_git_branch.split(",") if dist_git_branch else []
    config_dg_branches = []
    if isinstance(api.package_config, PackageConfig):
        config_dg_branches = (
            api.package_config.get_propose_downstream_dg_branches_value(
                pull_from_upstream=pull_from_upstream,
            )
        )

    default_dg_branch = api.dg.local_project.git_project.default_branch

    dg_branches = (
        cmdline_dg_branches or config_dg_branches or default_dg_branch.split(",")
    )
    return dg_branches, default_dg_branch


def get_dg_branches(api, dist_git_branch, pull_from_upstream=False):
    dg_branches, default_dg_branch = get_dist_git_branches(
        api,
        dist_git_branch,
        pull_from_upstream,
    )
    return get_branches(*dg_branches, default_dg_branch=default_dg_branch)


def sync_release(
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
    use_downstream_specfile,
    package_config,
    resolve_bug,
    sync_acls,
    check_for_non_git_upstream=False,
):
    api = get_packit_api(
        config=config,
        package_config=package_config,
        dist_git_path=dist_git_path,
        local_project=path_or_url,
        check_for_non_git_upstream=check_for_non_git_upstream,
    )
    if pr is None:
        pr = api.package_config.create_pr

    branches_to_update = get_dg_branches(
        api,
        dist_git_branch,
        pull_from_upstream=use_downstream_specfile,
    )

    click.echo(
        f"Proposing update of the following branches: {', '.join(branches_to_update)}",
    )

    dist_git_branches, default_dg_branch = get_dist_git_branches(
        api,
        dist_git_branch,
        pull_from_upstream=use_downstream_specfile,
    )
    branches_to_update = get_branches(
        *dist_git_branches,
        default_dg_branch=default_dg_branch,
    )
    for branch in branches_to_update:
        api.sync_release(
            dist_git_branch=branch,
            use_local_content=local_content,
            versions=[version] if version else [],
            force_new_sources=force_new_sources,
            upstream_ref=upstream_ref,
            create_pr=pr,
            force=force,
            use_downstream_specfile=use_downstream_specfile,
            resolved_bugs=resolve_bug,
            sync_acls=sync_acls,
            fast_forward_merge_branches=get_fast_forward_merge_branches_for(
                dist_git_branches=dist_git_branches,
                source_branch=branch,
                default=default_dg_branch,
            ),
        )


def sync_release_common_options(func):
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
        "--force",
        "-f",
        default=False,
        is_flag=True,
        help="Don't discard changes in the git repo by default, unless this is set.",
    )
    @click.option(
        "-b",
        "--resolve-bug",
        help="Bug(s) that are resolved with the update, e.g., rhbz#123 (multiple can be specified)",
        required=False,
        multiple=True,
        type=click.STRING,
    )
    @click.option(
        "--sync-acls",
        default=False,
        is_flag=True,
        help="Sync ACLs between dist-git repo and the fork, is considered only with --pr option.",
    )
    @click.option(
        PACKAGE_SHORT_OPTION,
        PACKAGE_LONG_OPTION,
        multiple=True,
        help=PACKAGE_OPTION_HELP.format(action="sync downstream"),
    )
    @click.argument(
        "path_or_url",
        type=LocalProjectParameter(),
        default=os.path.curdir,
    )
    @click.argument("version", required=False)
    @functools.wraps(func)
    def wrapper_common_options(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper_common_options


@click.command("propose-downstream", context_settings=get_context_settings())
@sync_release_common_options
@click.option(
    "--local-content",
    is_flag=True,
    default=False,
    help="Do not checkout release tag. Use the current state of the repo. "
    "This option is set by default for source-git repos",
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@pass_config
@cover_packit_exception
@iterate_packages
def propose_downstream(
    config,
    dist_git_path,
    dist_git_branch,
    force_new_sources,
    pr,
    path_or_url,
    version,
    local_content,
    upstream_ref,
    force,
    sync_acls,
    resolve_bug,
    package_config,
):
    """
    Land a new upstream release in Fedora using upstream packit config.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """
    sync_release(
        config=config,
        dist_git_path=dist_git_path,
        dist_git_branch=dist_git_branch,
        force_new_sources=force_new_sources,
        pr=pr,
        path_or_url=path_or_url,
        version=version,
        force=force,
        local_content=local_content,
        upstream_ref=upstream_ref,
        use_downstream_specfile=False,
        package_config=package_config,
        resolve_bug=resolve_bug,
        sync_acls=sync_acls,
    )


@click.command("pull-from-upstream", context_settings=get_context_settings())
@sync_release_common_options
@pass_config
@cover_packit_exception
@iterate_packages
def pull_from_upstream(
    config,
    dist_git_path,
    dist_git_branch,
    force_new_sources,
    pr,
    path_or_url,
    version,
    force,
    sync_acls,
    resolve_bug,
    package_config,
):
    """
    Land a new upstream release in Fedora using downstream packit config.

    PATH_OR_URL argument is a local path or a URL to the dist-git repository,
    it defaults to the current working directory

    VERSION argument is optional, the latest upstream version
    will be used by default
    """
    sync_release(
        config=config,
        dist_git_path=dist_git_path,
        dist_git_branch=dist_git_branch,
        force_new_sources=force_new_sources,
        pr=pr,
        path_or_url=path_or_url,
        version=version,
        force=force,
        local_content=False,
        upstream_ref=None,
        use_downstream_specfile=True,
        package_config=package_config,
        resolve_bug=resolve_bug,
        sync_acls=sync_acls,
        check_for_non_git_upstream=True,
    )
