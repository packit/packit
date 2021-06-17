# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
from typing import Optional

import click
import git

from packit.local_project import LocalProject
from packit.utils.repo import git_remote_url_to_https_url

logger = logging.getLogger(__name__)


class LocalProjectParameter(click.ParamType):
    """
    Path or url.
    """

    name = "path_or_url"

    def __init__(self, branch_param_name: str = None) -> None:
        """
        :param branch_param_name: name of the cli function parameter (not the option name)
        """
        super().__init__()
        self.branch_param_name = branch_param_name

    def convert(self, value, param, ctx):
        if isinstance(value, LocalProject):
            return value

        try:
            branch_name = None
            if self.branch_param_name:
                if self.branch_param_name in ctx.params:
                    branch_name = ctx.params[self.branch_param_name]
                else:  # use the default
                    for param in ctx.command.params:
                        if param.name == self.branch_param_name:
                            branch_name = param.default

            if os.path.isdir(value):
                absolute_path = os.path.abspath(value)
                logger.debug(f"Input is a directory: {absolute_path}")
                local_project = LocalProject(
                    working_dir=absolute_path,
                    ref=branch_name,
                    remote=ctx.obj.upstream_git_remote,
                )
            elif git_remote_url_to_https_url(value):
                logger.debug(f"Input is a URL to a git repo: {value}")
                local_project = LocalProject(
                    git_url=value, ref=branch_name, remote=ctx.obj.upstream_git_remote
                )
            else:
                self.fail(
                    "Provided input path_or_url is not a directory nor an URL of a git repo."
                )

            if not (local_project.working_dir or local_project.git_url):
                self.fail(
                    "Parameter is not an existing directory nor correct git url.",
                    param,
                    ctx,
                )
            return local_project
        except Exception as ex:
            self.fail(ex, param, ctx)


class GitRepoParameter(click.ParamType):
    """Parameter type to represent a Git repository on the local disk, and an
    optional branch, in the format <path>:<branch>.

    Attributes:
        from_ref_param: Name of the CLI parameter which tells the start point of the branch
            to be created, if the branch doesn't exist yet.
    """

    name = "git_repo"

    def __init__(self, from_ref_param: Optional[str] = None):
        super().__init__()
        self.from_ref_param = from_ref_param

    def convert(self, value, param, ctx) -> git.Repo:
        if isinstance(value, git.Repo):
            return value
        if not isinstance(value, str):
            self.fail(f"{value!r} is not a string")

        try:
            path, _, branch = value.partition(":")
            repo = git.Repo(path)
            if not branch:
                return repo

            branch_exists = True
            try:
                repo.rev_parse(branch)
            except git.BadName:
                branch_exists = False

            if self.from_ref_param is not None:
                if ctx.params.get(self.from_ref_param):
                    repo.git.checkout("-B", branch, ctx.params[self.from_ref_param])
                else:
                    self.fail(
                        f"Unable to create branch {branch!r} because "
                        f"{self.from_ref_param!r} is not specified",
                        param,
                        ctx,
                    )
            elif branch_exists:
                repo.git.checkout(branch)
            else:
                self.fail(
                    f"Cannot check out branch {branch!r} because it does not exist",
                    param,
                    ctx,
                )

            return repo

        except git.NoSuchPathError:
            self.fail(f"{path!r} does not exist", param, ctx)
        except git.GitCommandError as ex:
            self.fail(ex, param, ctx)
