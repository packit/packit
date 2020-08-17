# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Union

from packit.exceptions import PackitCommandFailedError
from packit.utils.logging import StreamLogger

logger = logging.getLogger(__name__)


def run_command(
    cmd: Union[List[str], str],
    error_message: str = None,
    cwd: Union[str, Path] = None,
    fail: bool = True,
    output: bool = False,
    env: Optional[Dict] = None,
    decode: bool = True,
    print_live: bool = False,
):
    """
    run provided command in a new subprocess

    :param cmd: 'duh
    :param error_message: if the command fails, output this error message
    :param cwd: run the command in
    :param fail: raise an exception when the command fails
    :param output: if True, return command's stdout & stderr
    :param env: set these env vars in the subprocess
    :param decode: decode stdout from utf8 to string
    :param print_live: print output from the command realtime to INFO log
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
    else:
        success = True

    if not output:
        return success

    o = stdout.get_output()
    return o.decode(sys.getdefaultencoding()) if decode else o


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
    wrapper for run_command method
    Indicating that this command run some action without local effect,
    or the effect is not important.

    eg.
        submit something to some server, and check how server reply
        call kinit of some ticket
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
