from pathlib import Path

from packit.utils import run_command, logger


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

        return run_command(
            cmd=[self.fedpkg_exec, "new-sources", sources],
            cwd=self.directory,
            error_message=f"Adding new sources failed:",
            fail=fail,
        )

    def build(self, scratch: bool = False):
        cmd = [self.fedpkg_exec, "build", "--nowait"]
        if scratch:
            cmd.append("--scratch")
        out = run_command(
            cmd=cmd,
            cwd=self.directory,
            error_message="Submission of build to koji failed.",
            fail=True,
            output=True,
        )
        logger.info("%s", out)

    def init_ticket(self, keytab: str = None):
        # TODO: this method has nothing to do with fedpkg, pull it out
        if not keytab:
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
        return run_command(
            cmd=cmd, error_message="Failed to init kerberos ticket:", fail=True
        )
