# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from packit.exceptions import PackitCommandFailedError
from packit.utils.logging import StreamLogger

logger = logging.getLogger(__name__)


# TODO: Switch to dataclass when possible
class CommandResult:
    """
    Structure to represent a result of the command that was run.

    Attributes:
        success: Boolean value holding a result of the command.
        stdout: Holds standard output of the command, in case it was requsted.
        stderr: Holds standard error output of the command, in case it was requsted.

    Both `stdout` and `stderr` can be represented by bytes or string, depending
    on the provided `decode` argument to the `run_command`.
    """

    def __init__(
        self,
        success: bool = False,
        stdout: Union[str, bytes, None] = None,
        stderr: Union[str, bytes, None] = None,
    ) -> None:
        self.success = success
        self.stdout = stdout
        self.stderr = stderr


def run_command(
    cmd: Union[List[str], str],
    error_message: Optional[str] = None,
    cwd: Union[str, Path, None] = None,
    fail: bool = True,
    output: bool = False,
    env: Optional[Dict] = None,
    decode: bool = True,
    print_live: bool = False,
) -> CommandResult:
    """
    Run provided command in a new subprocess.

    Args:
        cmd: Command to be run.
        error_message: Error message to be included in the exception and logs in
            case the command fails.

            Defaults to generic message with the escaped command.
        cwd: Working directory of the new subprocess.

            Defaults to current working directory of the process itself.
        fail: Raise an exception if the command fails.

            Defaults to `True`.
        output: Return the output of the subprocess.

            Defaults to `False`.
        env: Environment variables to be set in the newly created subprocess.

            Defaults to none.
        decode: Decode the output of the subprocess in the system's default
            encoding.

            Defaults to `True`.
        print_live: Print real-time output of the command as INFO.

            Defaults to `False`.

    Returns:
        In case `output = False`, returns boolean that indicates success of the
        command that was run.

        Otherwise returns pair of `stdout` and `stderr` produced by the subprocess.
        It can be pair of bytes or string, depending on the value of `decode` parameter.
    """
    if not isinstance(cmd, list):
        cmd = shlex.split(cmd)

    escaped_command = " ".join(cmd)

    logger.debug(f"Command: {escaped_command}")

    cwd = str(cwd) if cwd else str(Path.cwd())
    error_message = error_message or f"Command {escaped_command!r} failed."

    # we need to pass complete env to Popen, otherwise we lose everything from os.environ
    cmd_env = os.environ
    if env:
        cmd_env.update(env)

    # we can't use universal newlines here b/c the output from the command can be encoded
    # in something alien and we would "can't decode this using utf-8" errors
    # https://github.com/packit/systemd-rhel8-flock/pull/9#issuecomment-550184016
    shell = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
        env=cmd_env,
    )

    stdout = StreamLogger(
        shell.stdout,
        log_level=logging.DEBUG if not print_live else logging.INFO,
        decode=decode,
    )
    stderr = StreamLogger(
        shell.stderr,
        log_level=logging.DEBUG if not print_live else logging.INFO,
        decode=decode,
    )

    stdout.start()
    stderr.start()
    shell.wait()
    stdout.join()
    stderr.join()

    success = True  # default is success
    if shell.returncode != 0:
        logger.error(f"{error_message}")
        if fail:
            stderr_output = (
                stderr.get_output().decode() if decode else stderr.get_output()
            )
            stdout_output = (
                stdout.get_output().decode() if decode else stdout.get_output()
            )
            if output:
                logger.debug(f"Command stderr: {stderr_output}")
                logger.debug(f"Command stdout: {stdout_output}")
            raise PackitCommandFailedError(
                f"{error_message}",
                stdout_output=stdout_output,
                stderr_output=stderr_output,
            )
        success = False

    if not output:
        return CommandResult(success=success)

    command_output: Union[Tuple[str, str], Tuple[bytes, bytes]] = map(
        lambda out: out.get_output(), (stdout, stderr)
    )
    if decode:
        command_output = map(
            lambda out: out.decode(sys.getdefaultencoding()), command_output
        )

    out, err = command_output
    return CommandResult(success, out, err)


def run_command_remote(
    cmd,
    error_message=None,
    cwd=None,
    fail=True,
    output=False,
    env: Optional[Dict] = None,
    decode=True,
    print_live: bool = False,
):
    """
    Wrapper for the `run_command` method.

    Indicating that this command run some action without local effect,
    or the effect is not important.

    For example submit something to some server, and check how server reply, e.g.
    call kinit to obtain a ticket.
    """
    return run_command(
        cmd, error_message, cwd, fail, output, env, decode=decode, print_live=print_live
    )


@contextmanager
def cwd(target: Union[str, Path]):
    """
    Manage cwd in a pushd/popd fashion.

    Usage:

        with cwd(tmpdir):
          do something in tmpdir
    """
    curdir = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(curdir)
