# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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
from typing import Optional

from packit import utils  # so we can mock utils
from packit.utils import logger


class FedPKG:
    """
    Part of the code is from release-bot:

    https://github.com/user-cont/release-bot/blob/master/release_bot/fedora.py
    """

    def __init__(
        self, fas_username: str = None, directory: str = None, stage: bool = False
    ):
        self.fas_username = fas_username
        self.directory = directory
        self.stage = stage
        if stage:
            self.fedpkg_exec = "fedpkg-stage"
        else:
            self.fedpkg_exec = "fedpkg"

    def new_sources(self, sources="", fail=True):
        if not Path(self.directory).is_dir():
            raise Exception("Cannot access fedpkg repository:")

        return utils.run_command_remote(
            cmd=[self.fedpkg_exec, "new-sources", sources],
            cwd=self.directory,
            error_message=f"Adding new sources failed:",
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
        :return:
        """
        cmd = [self.fedpkg_exec, "build"]
        if scratch:
            cmd.append("--scratch")
        if nowait:
            cmd.append("--nowait")
        if koji_target:
            cmd += ["--target", koji_target]
        if srpm_path:
            cmd += ["--srpm", str(srpm_path)]
        utils.run_command_remote(
            cmd=cmd,
            cwd=self.directory,
            error_message="Submission of build to koji failed.",
            fail=True,
        )

    def clone(self, package_name: str, target_path: str, anonymous: bool = False):
        """
        clone a dist-git repo; this has to be done in current env
        b/c we don't have the keytab in sandbox
        """
        cmd = [self.fedpkg_exec]
        if self.fas_username:
            cmd += ["--user", self.fas_username]
        cmd += ["-q", "clone"]
        if anonymous:
            cmd += ["-a"]
        cmd += [package_name, target_path]
        utils.run_command(cmd=cmd)

    def init_ticket(self, keytab: str = None):
        # TODO: this method has nothing to do with fedpkg, pull it out
        if not keytab and not self.fas_username:
            logger.info("won't be doing kinit, no credentials provided")
            return
        if keytab and Path(keytab).is_file():
            cmd = [
                "kinit",
                f"{self.fas_username}@FEDORAPROJECT.ORG",
                "-k",
                "-t",
                keytab,
            ]
        else:
            # there is no keytab, but user still might have active ticket - try to renew it
            cmd = ["kinit", "-R", f"{self.fas_username}@FEDORAPROJECT.ORG"]
        return utils.run_command_remote(
            cmd=cmd, error_message="Failed to init kerberos ticket:", fail=True
        )
