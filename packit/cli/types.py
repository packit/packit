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

    def __init__(
        self,
        ref_param_name: Optional[str] = None,
        pr_id_param_name: Optional[str] = None,
        merge_pr_param_name: Optional[str] = None,
        target_branch_param_name: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.ref_param_name = ref_param_name
        self.pr_id_param_name = pr_id_param_name
        self.merge_pr_param_name = merge_pr_param_name
        self.target_branch_param_name = target_branch_param_name

    @staticmethod
    def get_param(param_name, ctx):
        value = None
        if param_name in ctx.params:
            value = ctx.params[param_name]
        else:  # use the default
            for param in ctx.command.params:
                if param.name == param_name:
                    value = param.default
        return value

    def convert(self, value, param, ctx):
        if isinstance(value, LocalProject):
            return value

        try:
            pr_id = None
            merge_pr = True
            target_branch = None

            ref = (
                self.get_param(self.ref_param_name, ctx) if self.ref_param_name else ""
            )
            if self.pr_id_param_name:
                pr_id = self.get_param(self.pr_id_param_name, ctx)

            if self.merge_pr_param_name:
                merge_pr = self.get_param(self.merge_pr_param_name, ctx)

            if self.target_branch_param_name:
                target_branch = self.get_param(self.target_branch_param_name, ctx)

            if os.path.isdir(value):
                absolute_path = os.path.abspath(value)
                logger.debug(f"Input is a directory: {absolute_path}")
                local_project = LocalProject(
                    working_dir=absolute_path,
                    ref=ref,
                    remote=ctx.obj.upstream_git_remote,
                    merge_pr=merge_pr,
                    target_branch=target_branch,
                )
            elif git_remote_url_to_https_url(value):
                logger.debug(f"Input is a URL to a git repo: {value}")
                local_project = LocalProject(
                    git_url=value,
                    ref=ref,
                    remote=ctx.obj.upstream_git_remote,
                    pr_id=pr_id,
                    merge_pr=merge_pr,
                    target_branch=target_branch,
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
