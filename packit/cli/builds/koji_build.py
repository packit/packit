# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import getcwd

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import get_context_settings, pass_config
from packit.config.aliases import get_branches, get_koji_targets
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)
from packit.exceptions import (
    PackitCommandFailedError,
    PackitConfigException,
    ensure_str,
)
from packit.utils.changelog_helper import ChangelogHelper

logger = logging.getLogger(__name__)


@click.command("in-koji", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Comma separated list of target branches in dist-git to release into. "
    "(defaults to repo's default branch)",
)
@click.option(
    "--dist-git-path",
    help="Path to dist-git repo to work in. "
    "Otherwise clone the repo in a temporary directory.",
)
@click.option(
    "--from-upstream",
    help="Build the project in koji directly from the upstream repository",
    is_flag=True,
    default=False,
)
@click.option(
    "--koji-target",
    help="Koji target to build inside (see `koji list-targets`).",
)
@click.option(
    "--scratch",
    is_flag=True,
    default=False,
    help="Submit a scratch koji build",
)
@click.option("--wait/--no-wait", default=True, help="Wait for the build to finish")
@click.option(
    "--release-suffix",
    default=None,
    type=click.STRING,
    help="Specifies release suffix. Allows to override default generated:"
    "{current_time}.{sanitized_current_branch}{git_desc_suffix}",
)
@click.option(
    "--default-release-suffix",
    default=False,
    is_flag=True,
    help=(
        "Allows to use default, packit-generated, release suffix when some "
        "release_suffix is specified in the configuration."
    ),
)
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="build"),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=getcwd())
@pass_config
@cover_packit_exception
@iterate_packages
def koji(
    config,
    dist_git_path,
    dist_git_branch,
    from_upstream,
    koji_target,
    scratch,
    wait,
    release_suffix,
    default_release_suffix,
    package_config,
    path_or_url,
):
    """
    Build selected upstream project in Fedora.

    By default, packit checks out the respective dist-git repository and performs
    `fedpkg build` for the selected branch. With `--from-upstream`, packit creates a SRPM
    out of the current checkout and sends it to koji.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config,
        package_config=package_config,
        dist_git_path=dist_git_path,
        local_project=path_or_url,
    )
    release_suffix = ChangelogHelper.resolve_release_suffix(
        api.package_config,
        release_suffix,
        default_release_suffix,
    )

    default_dg_branch = api.dg.local_project.git_project.default_branch
    dist_git_branch = dist_git_branch or default_dg_branch
    branches_to_build = get_branches(
        *dist_git_branch.split(","),
        default_dg_branch=default_dg_branch,
    )
    package = (
        package_config.downstream_package_name
        if package_config.downstream_package_name
        else package_config.upstream_package_name
    )
    click.echo(
        f"Building from the following branches: {', '.join(branches_to_build)}, "
        f"for package {package}",
    )

    targets_to_build = {None} if koji_target is None else get_koji_targets(koji_target)

    if len(targets_to_build) > 1 and len(branches_to_build) > 1:
        raise PackitConfigException(
            "Parameters --dist-git-branch and --koji-target cannot have "
            "multiple values at the same time.",
        )

    build_futures = {}
    with ThreadPoolExecutor() as executor:
        for target in targets_to_build:
            for branch in branches_to_build:
                click.echo(
                    f"Starting build for branch '{branch}', target '{target}'...",
                )
                build_futures[
                    executor.submit(
                        api.build,
                        dist_git_branch=branch,
                        scratch=scratch,
                        nowait=not wait,
                        koji_target=target,
                        from_upstream=from_upstream,
                        release_suffix=release_suffix,
                        srpm_path=config.srpm_path,
                    )
                ] = (branch, target)

        for future in as_completed(build_futures):
            branch, target = build_futures[future]
            try:
                out = future.result()
                click.echo(f"Completed build for branch '{branch}', target '{target}'.")
            except PackitCommandFailedError as ex:
                logs_stdout = "\n>>> ".join(ex.stdout_output.strip().split("\n"))
                logs_stderr = "\n!!! ".join(ex.stderr_output.strip().split("\n"))
                click.echo(
                    f"Build for branch '{branch}', target '{target}' failed. \n"
                    f">>> {logs_stdout}\n"
                    f"!!! {logs_stderr}\n",
                    err=True,
                )
            else:
                if out:
                    click.echo(ensure_str(out))

        click.echo("All builds processed.")
