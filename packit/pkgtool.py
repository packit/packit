# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Union

from packit.exceptions import PackitCommandFailedError
from packit.utils import commands  # so we can mock utils
from packit.utils.logging import logger


class PkgTool:
    """
    Wrapper around fedpkg/centpkg/cbs.
    """

    def __init__(
        self,
        fas_username: Optional[str] = None,
        directory: Union[Path, str, None] = None,
        tool: str = "fedpkg",
        sig: Optional[str] = None,
    ):
        """
        Args:
            fas_username: FAS username (used for cloning)
            directory: operate in this dist-git repository
            tool: pkgtool to use (fedpkg, centpkg, centpkg-sig)
            sig: name of the SIG; used for adjusting the path during cloning
        """
        self.fas_username = fas_username
        self.directory = Path(directory) if directory else None
        self.tool = tool
        self.sig = sig

    def __repr__(self):
        return (
            "PkgTool("
            f"fas_username='{self.fas_username}', "
            f"directory='{self.directory}', "
            f"sig='{self.sig}', "
            f"tool='{self.tool}')"
        )

    def new_sources(
        self,
        sources: Optional[Iterable[Path]] = None,
        fail: bool = True,
        offline: bool = False,
    ):
        sources = sources or []
        if not self.directory.is_dir():
            raise Exception(f"Cannot access {self.tool} repository: {self.directory}")

        cmd = [self.tool, "new-sources"]
        if offline:
            cmd.append("--offline")
        sources_ = [str(source) for source in sources] if sources else []
        return commands.run_command_remote(
            cmd=cmd + sources_,
            cwd=self.directory,
            error_message="Adding new sources failed:",
            print_live=True,
            fail=fail,
        ).success

    def sources(self, fail: bool = True) -> bool:
        """Run the 'sources' command

        Args:
            fail: Raise an exception if the command fails

        Returns:
            True, if the command finished successfully, False otherwise.
        """
        return commands.run_command_remote(
            cmd=[self.tool, "sources"],
            cwd=self.directory,
            error_message="Downloading source files from the lookaside cache failed:",
            print_live=True,
            fail=fail,
        ).success

    def build(
        self,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
        srpm_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Run build in Koji.

        Args:
            scratch: scratch (temporary) build or not?
            nowait: False == wait for the build to finish
            koji_target: koji target to build in (`koji list-targets`)
            srpm_path: use selected SRPM for build, not dist-git repo & ref

        Returns:
            The 'stdout' of the build command.
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
            return commands.run_command_remote(
                cmd=cmd,
                cwd=self.directory,
                error_message="Submission of build to koji failed.",
                fail=True,
                output=True,
                print_live=True,
            ).stdout

        except PackitCommandFailedError as ex:
            # fail on the fedpkg side, the build is triggered
            if (
                "watch_tasks() got an unexpected keyword argument 'ki_handler'"
                in ex.stderr_output
            ):
                logger.info(
                    f"'{self.tool} build' crashed. It is a known issue: "
                    "the build is submitted in koji anyway.",
                )
                logger.debug(ex.stdout_output)
                return ""

            raise

    def clone(
        self,
        package_name: str,
        target_path: Union[Path, str],
        branch: Optional[str] = None,
        anonymous: bool = False,
    ):
        """
        clone a dist-git repo; this has to be done in current env
        b/c we don't have the keytab in sandbox
        """
        cmd = [self.tool]
        if self.fas_username:
            cmd += ["--user", self.fas_username]
        cmd += ["-q", "clone"]
        if branch:
            cmd += ["--branch", branch]
        if anonymous:
            cmd += ["--anonymous"]

        cmd += [
            f"{self.sig}/rpms/{package_name}" if self.sig else package_name,
            str(target_path),
        ]

        error_msg = (
            f"{self.tool} failed to clone repository {package_name}; "
            "please make sure that you are authorized to clone repositories "
            "from Fedora dist-git - this may require SSH keys set up or "
            "Kerberos ticket being active."
        )
        commands.run_command(cmd=cmd, error_message=error_msg)

    def verrel(self) -> str:
        """
        Run the `verrel` command.
        """
        return commands.run_command(
            cmd=[self.tool, "verrel"],
            cwd=self.directory,
            output=True,
            error_message=f"`{self.tool} verrel` was not successfull",
        ).stdout.strip()
