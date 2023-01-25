# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import functools
from os import getcwd

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.config.aliases import get_branches, get_koji_targets
from packit.exceptions import PackitCommandFailedError, ensure_str
from packit.exceptions import PackitConfigException
from packit.utils.changelog_helper import ChangelogHelper
from packit.config import get_local_package_config
from packit.config.common_package_config import MultiplePackages

logger = logging.getLogger(__name__)


def iterate_packages(func):
    """
    Decorator for dealing with packages in a package configuration

    * if packages are specified as an option in CLI then
      do a koji build just for them
    * if packages are not specified as an option in CLI but
      there are multiple packages in the configuration
      then do a koji build for all of them
    * if there is just one package in the configuration
      then do a single koji build

    This method (iterate_packages) **has not** "package_config"
    in its kwargs but calls a method (func) who needs a
    package_config in its args!
    """

    @functools.wraps(func)
    def covered_func(*args, **kwargs):
        path_or_url = kwargs["path_or_url"]
        config = kwargs["config"]
        packages_config: MultiplePackages = get_local_package_config(
            path_or_url.working_dir,
            repo_name=path_or_url.repo_name,
            try_local_dir_last=True,
            package_config_path=config.package_config_path,
        )
        if "packages" in kwargs and kwargs["packages"]:
            for package in kwargs["packages"].split(","):
                kwargs["package_config"] = packages_config.packages[package]
                func(*args, **kwargs)
        elif hasattr(packages_config, "packages"):
            for _, package_config in packages_config.packages.items():
                kwargs["package_config"] = package_config
                func(*args, **kwargs)
        else:
            kwargs["package_config"] = packages_config
            func(*args, **kwargs)

    return covered_func


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
    "--koji-target", help="Koji target to build inside (see `koji list-targets`)."
)
@click.option(
    "--scratch", is_flag=True, default=False, help="Submit a scratch koji build"
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
    "--packages",
    help=(
        "Comma separated list of packages to be built. "
        "(defaults to all the packages listed inside the config)"
    ),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=getcwd())
@pass_config
@cover_packit_exception
@iterate_packages
def koji(
    config,
    package_config,
    dist_git_path,
    dist_git_branch,
    from_upstream,
    koji_target,
    scratch,
    wait,
    release_suffix,
    default_release_suffix,
    packages,
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
        api.package_config, release_suffix, default_release_suffix
    )

    default_dg_branch = api.dg.local_project.git_project.default_branch
    dist_git_branch = dist_git_branch or default_dg_branch
    branches_to_build = get_branches(
        *dist_git_branch.split(","), default_dg_branch=default_dg_branch
    )
    click.echo(f"Building from the following branches: {', '.join(branches_to_build)}")

    if koji_target is None:
        targets_to_build = {None}
    else:
        targets_to_build = get_koji_targets(koji_target)

    if len(targets_to_build) > 1 and len(branches_to_build) > 1:
        raise PackitConfigException(
            "Parameters --dist-git-branch and --koji-target cannot have "
            "multiple values at the same time."
        )

    for target in targets_to_build:
        for branch in branches_to_build:
            try:
                out = api.build(
                    dist_git_branch=branch,
                    scratch=scratch,
                    nowait=not wait,
                    koji_target=target,
                    from_upstream=from_upstream,
                    release_suffix=release_suffix,
                    srpm_path=config.srpm_path,
                )
            except PackitCommandFailedError as ex:
                logs_stdout = "\n>>> ".join(ex.stdout_output.strip().split("\n"))
                logs_stderr = "\n!!! ".join(ex.stderr_output.strip().split("\n"))
                click.echo(
                    f"Build for branch '{branch}' failed. \n"
                    f">>> {logs_stdout}\n"
                    f"!!! {logs_stderr}\n",
                    err=True,
                )
            else:
                if out:
                    print(ensure_str(out))
