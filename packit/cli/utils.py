# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
import functools
import logging
import sys
import pathlib
from pathlib import Path
from typing import List, Optional, Union

import click
from github import GithubException

from ogr.parsing import parse_git_repo

from packit.config.package_config import PackageConfig
from packit.config.common_package_config import MultiplePackages

from packit.api import PackitAPI
from packit.config import Config, get_local_package_config, JobType
from packit.constants import DIST_GIT_HOSTNAME_CANDIDATES
from packit.constants import DISTRO_DIR, SRC_GIT_CONFIG
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


def iterate_packages(func):
    """
    Decorator for dealing with sub-packages in a package (Monorepo) configuration

    * if packages are specified as an option in CLI then
      call decorated function just for them
    * if packages are not specified as an option in CLI but
      there are multiple packages in the configuration
      then call the decorated function for all of them
    * if there is just one package in the configuration
      then call the decorated function just once

    This method (iterate_packages) **has not** `package_config` key
    in its kwargs, it has `packages`, but calls a method
    (func) who needs a `package_config` key and not `packages`!
    """

    @functools.wraps(func)
    def covered_func(*args, **kwargs):
        path_or_url = kwargs["path_or_url"]
        config = kwargs["config"]
        decorated_func_kwargs = kwargs.copy()
        del decorated_func_kwargs["package"]
        packages_config: MultiplePackages = get_local_package_config(
            path_or_url.working_dir,
            repo_name=path_or_url.repo_name,
            try_local_dir_last=True,
            package_config_path=config.package_config_path,
        )
        packages_config_views_names = set(
            packages_config.get_package_config_views().keys()
        )
        if kwargs.get("package"):
            if not_defined_packages := set(kwargs["package"]).difference(
                packages_config_views_names
            ):
                logger.error(
                    "Packages %s are not defined in packit configuration.",
                    not_defined_packages,
                )
                return None
            for package in kwargs["package"]:
                decorated_func_kwargs["config"] = copy.deepcopy(
                    config
                )  # reset working variables like srpm_path
                decorated_func_kwargs[
                    "package_config"
                ] = packages_config.get_package_config_views()[package]
                func(*args, **decorated_func_kwargs)
        elif hasattr(packages_config, "packages"):
            for package_config in packages_config.get_package_config_views().values():
                decorated_func_kwargs["config"] = copy.deepcopy(
                    config
                )  # reset working variables like srpm_path
                decorated_func_kwargs["package_config"] = package_config
                func(*args, **decorated_func_kwargs)
        else:
            logger.error("Given packages_config has no packages attribute")

    return covered_func


def iterate_packages_source_git(func):
    """
    Decorator for dealing with sub-packages in a package (Monorepo) configuration
    Designed for source-git related commands.

    * if dist-git-path is a git repo
      then search for a downstream repo name match
      in the configuration and find out its PackageConfig(View)
      but if there is just one package config and not matches
      then try going on with the found package config
    * if there are multiple package configs and
      dist-git-path is a dir (and not a git repo)
      for every sub-dir which is also a git repo
      search for a downstream repo name match
      in the configuration and find out its PackageConfig(View)
      Invoke the decorated function as many time as we
      found a match

    This method (iterate_packages) **has not** `package_config` key
    in its kwargs, but calls a method
    (func) who needs a `package_config` key!
    """

    @functools.wraps(func)
    def covered_func(*args, **kwargs):
        source_git = kwargs["source_git"]
        dist_git = kwargs["dist_git"]
        config = kwargs["config"]
        decorated_func_kwargs = kwargs.copy()

        source_git_path = pathlib.Path(source_git).resolve()
        dist_git_path = pathlib.Path(dist_git).resolve()

        packages_config = get_local_package_config(
            package_config_path=source_git_path / DISTRO_DIR / SRC_GIT_CONFIG
        )

        found_func = False
        for package in packages_config.get_package_config_views().values():
            if package.downstream_package_name == dist_git_path.name:
                decorated_func_kwargs["config"] = copy.deepcopy(
                    config
                )  # reset working variables like srpm_path
                decorated_func_kwargs["package_config"] = package
                func(*args, **decorated_func_kwargs)
                found_func = True

        # if names does not match but there is just one package try it
        if (
            len(packages_config.get_package_config_views()) == 1
            and dist_git_path.joinpath(".git").exists()
            and not found_func
        ):
            decorated_func_kwargs["config"] = copy.deepcopy(
                config
            )  # reset working variables like srpm_path
            decorated_func_kwargs["package_config"] = list(
                packages_config.get_package_config_views().values()
            )[0]
            func(*args, **decorated_func_kwargs)
            found_func = True

        # probably, if dist-git is not a git repo,
        # we would like to cycle over multiple dist-git repos
        elif (
            dist_git_path.is_dir()
            and not dist_git_path.joinpath(".git").exists()
            and not found_func
        ):
            repo_dirs = [
                p
                for p in dist_git_path.glob("*")
                if p.is_dir() and p.joinpath(".git").exists()
            ]
            for package in packages_config.get_package_config_views().values():
                for repo_dir in repo_dirs:
                    if package.downstream_package_name == repo_dir.name:
                        decorated_func_kwargs["config"] = copy.deepcopy(
                            config
                        )  # reset working variables like srpm_path
                        decorated_func_kwargs["dist_git"] = str(repo_dir)
                        decorated_func_kwargs["package_config"] = package
                        func(*args, **decorated_func_kwargs)
                        found_func = True

        if not found_func:
            logger.error(
                f"No match found for source git {source_git} and dist git {dist_git}."
            )

    return covered_func


def get_packit_api(
    config: Config,
    local_project: LocalProject,
    package_config: Optional[Union[PackageConfig, MultiplePackages]] = None,
    dist_git_path: Optional[str] = None,
    job_config_index: Optional[int] = None,
    job_type: Optional[JobType] = None,
) -> PackitAPI:
    """
    Load the package config, set other options and return the PackitAPI
    """
    if not package_config:
        # TODO: to be removed when monorepo refactoring is finished!
        package_config = get_local_package_config(
            local_project.working_dir,
            repo_name=local_project.repo_name,
            try_local_dir_last=True,
            package_config_path=config.package_config_path,
        )
    logger.debug(f"job_config_index: {job_config_index}")
    if job_config_index is not None and isinstance(package_config, PackageConfig):
        if job_config_index >= len(package_config.jobs):
            raise PackitException(
                "job_config_index is bigger than number of jobs in package config!"
            )
        package_config = package_config.jobs[job_config_index]
        logger.debug(f"Final package (job) config: {package_config}")
    elif job_type is not None:
        try:
            package_config = [
                job for job in package_config.jobs if job.type == job_type
            ][0]
        except IndexError:
            raise PackitException(
                f"No job with type {job_type} found in package config."
            )
        logger.debug(f"Final package (job) config: {package_config}")

    if dist_git_path and Path(dist_git_path) == local_project.working_dir:
        return PackitAPI(
            config=config,
            package_config=package_config,
            upstream_local_project=None,
            downstream_local_project=local_project,
            dist_git_clone_path=dist_git_path,
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
        dist_git_clone_path=dist_git_path,
    )


def get_hostname_or_none(url: str) -> Optional[str]:
    parsed_url = parse_git_repo(potential_url=url)
    if parsed_url:
        return parsed_url.hostname
    return None
