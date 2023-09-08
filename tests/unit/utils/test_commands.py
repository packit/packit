# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packit.utils.commands import run_command


def test_run_command_w_env():
    run_command(["bash", "-c", "env | grep PATH"], env={"X": "Y"})
