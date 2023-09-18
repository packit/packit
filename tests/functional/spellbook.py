# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import subprocess
from subprocess import STDOUT


def call_real_packit(parameters=None, envs=None, cwd=None, return_output=False):
    """invoke packit in a subprocess"""
    cmd = ["python3", "-m", "packit.cli.packit_base", *parameters]
    if return_output:
        return subprocess.check_output(cmd, env=envs, cwd=cwd, stderr=STDOUT)
    return subprocess.check_call(cmd, env=envs, cwd=cwd)


def call_real_packit_and_return_exit_code(parameters=None, envs=None, cwd=None):
    """invoke packit in a subprocess and return exit code"""
    cmd = ["python3", "-m", "packit.cli.packit_base", *parameters]
    return subprocess.call(cmd, env=envs, cwd=cwd)
