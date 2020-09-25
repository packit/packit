# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os

import click

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
