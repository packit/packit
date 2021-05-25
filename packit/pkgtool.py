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

from pathlib import Path
from typing import Optional, Union

from packit.exceptions import PackitCommandFailedError

from packit.utils import commands  # so we can mock utils
from packit.utils.logging import logger


class PkgTool:
    """
    Wrapper around fedpkg/centpkg.
    """

    def __init__(
        self,
        fas_username: str = None,
        directory: Union[Path, str] = None,
        tool: str = "fedpkg",
    ):
        self.fas_username = fas_username
        self.directory = Path(directory) if directory else None
        self.tool = tool

    def __repr__(self):
        return (
            "PkgTool("
            f"fas_username='{self.fas_username}', "
            f"directory='{self.directory}', "
            f"tool='{self.tool}')"
        )

    def new_sources(self, sources: Optional[Path] = None, fail: bool = True):
        if not self.directory.is_dir():
            raise Exception(f"Cannot access {self.tool} repository: {self.directory}")

        sources_ = str(sources) if sources else ""
        return commands.run_command_remote(
            cmd=[self.tool, "new-sources", sources_],
            cwd=self.directory,
            error_message="Adding new sources failed:",
            print_live=True,
            fail=fail,
        )

    def build(
        self,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
        srpm_path: Optional[Path] = None,
    ):
        """
        build in koji

        :param scratch: scratch (temporary) build or not?
        :param nowait: False == wait for the build to finish
        :param koji_target: koji target to build in (`koji list-targets`)
        :param srpm_path: use selected SRPM for build, not dist-git repo & ref
        """
        cmd = [self.tool, "build"]
        if scratch:
            cmd.append("--scratch")
        if nowait:
            cmd.append("--nowait")
        if koji_target:
            cmd += ["--target", koji_target]
        if srpm_path:
            cmd += ["--srpm", str(srpm_path)]

        try:
            commands.run_command_remote(
                cmd=cmd,
                cwd=self.directory,
                error_message="Submission of build to koji failed.",
                fail=True,
            )

        except PackitCommandFailedError as ex:
            # fail on the fedpkg side, the build is triggered
            if (
                "watch_tasks() got an unexpected keyword argument 'ki_handler'"
                in ex.stderr_output
            ):
                logger.info(
                    f"'{self.tool} build' crashed. It is a known issue: "
                    "the build is submitted in koji anyway."
                )
                logger.debug(ex.stdout_output)

            else:
                raise

    def clone(self, package_name: str, target_path: str, anonymous: bool = False):
        """
        clone a dist-git repo; this has to be done in current env
        b/c we don't have the keytab in sandbox
        """
        cmd = [self.tool]
        if self.fas_username:
            cmd += ["--user", self.fas_username]
        cmd += ["-q", "clone"]
        if anonymous:
            cmd += ["-a"]
        cmd += [package_name, target_path]

        error_msg = (
            f"Packit failed to clone the repository {package_name}; "
            "please make sure that you are authorized to clone repositories "
            "from Fedora dist-git - this may require SSH keys set up or "
            "Kerberos ticket being active."
        )
        commands.run_command(cmd=cmd, error_message=error_msg)
