# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packit.utils.commands import run_command


def remove_gpg_key_pair(gpg_binary: str, fingerprint: str):
    run_command(
        [gpg_binary, "--batch", "--yes", "--delete-secret-and-public-key", fingerprint]
    )
