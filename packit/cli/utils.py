# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import functools
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from github import GithubException

from ogr.parsing import parse_git_repo
from packit.config.common_package_config import CommonPackageConfig
from packit.config.package_config import PackageConfig

from packit.api import PackitAPI
from packit.config import Config, get_local_package_config
from packit.constants import DIST_GIT_HOSTNAME_CANDIDATES
from packit.exceptions import PackitException, PackitNotAGitRepoException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


def cover_packit_exception(_func=None, *, exit_code=None):
    """
    Decorator for executing the function in the try-except block.

    The PackitException is caught and
    - raised in debug
    - sys.exit(exit_code), otherwise

    On other Exceptions we print the message about creating an issue.


    If the function receives config, it recognises the debug mode.
    => use it after the @pass_config decorator
    """

    def decorator_cover(func):
        @functools.wraps(func)
        def covered_func(config=None, *args, **kwargs):
            try:
                if config:
                    func(config=config, *args, **kwargs)
                else:
                    func(*args, **kwargs)
            except KeyboardInterrupt:
                click.echo("Quitting on user request.")
                sys.exit(1)
            except PackitException as exc:
                if config and config.debug:
                    logger.exception(exc)
                else:
                    logger.error(exc)
                sys.exit(exit_code or 2)
            except GithubException as exc:
                if config and config.debug:
                    logger.exception(exc)
                else:
                    click.echo(
                        "We've encountered an error while talking to GitHub API, please make sure"
                        " that you pass GitHub API token and it has correct permissions, \n"
                        f"precise error message: {exc} \n"
                        "https://github.com/packit/packit/tree/master/docs\n"
                    )
                sys.exit(exit_code or 3)
            except Exception as exc:
                if config and config.debug:
                    logger.exception(exc)
                else:
                    logger.error(exc)
                    click.echo(
                        "Unexpected exception occurred,\n"
                        "please fill an issue here:\n"
                        "https://github.com/packit/packit/issues",
                        err=True,
                    )
                sys.exit(exit_code or 4)

        return covered_func

    if _func is None:
        return decorator_cover
    else:
        return decorator_cover(_func)


def get_packit_api(
    config: Config,
    local_project: LocalProject,
    dist_git_path: str = None,
    load_packit_yaml: bool = True,
    job_config: Optional[CommonPackageConfig] = None,
) -> PackitAPI:
    """
    Load the package config, set other options and return the PackitAPI
    """
    if job_config:
        package_config = job_config
    elif load_packit_yaml:
        package_config = get_local_package_config(
            local_project.working_dir,
            repo_name=local_project.repo_name,
            try_local_dir_last=True,
            package_config_path=config.package_config_path,
        )
    else:
        package_config = PackageConfig()

    if dist_git_path:
        package_config.dist_git_clone_path = dist_git_path

    if dist_git_path and Path(dist_git_path) == local_project.working_dir:
        return PackitAPI(
            config=config,
            package_config=package_config,
            upstream_local_project=None,
            downstream_local_project=local_project,
        )

    if not local_project.git_repo:
        raise PackitNotAGitRepoException(
            f"{local_project.working_dir!r} is not a git repository."
        )

    remote_urls: List[str] = []
    for remote in local_project.git_repo.remotes:
        remote_urls += remote.urls

    upstream_hostname = (
        get_hostname_or_none(url=package_config.upstream_project_url)
        if package_config.upstream_project_url
        else None
    )

    lp_upstream = None
    lp_downstream = None

    for url in remote_urls:
        remote_hostname = get_hostname_or_none(url=url)
        if not remote_hostname:
            continue

        if upstream_hostname and remote_hostname == upstream_hostname:
            lp_upstream = local_project
            logger.debug("Input directory is an upstream repository.")
            break

        if package_config.dist_git_base_url and (
            remote_hostname in package_config.dist_git_base_url
            or remote_hostname in DIST_GIT_HOSTNAME_CANDIDATES
        ):
            lp_downstream = local_project
            logger.debug("Input directory is a downstream repository.")
            break
    else:
        lp_upstream = local_project
        # fallback, this is the past behavior
        logger.debug("Input directory is an upstream repository.")

    return PackitAPI(
        config=config,
        package_config=package_config,
        upstream_local_project=lp_upstream,
        downstream_local_project=lp_downstream,
    )


def get_hostname_or_none(url: str) -> Optional[str]:
    parsed_url = parse_git_repo(potential_url=url)
    if parsed_url:
        return parsed_url.hostname
    return None
