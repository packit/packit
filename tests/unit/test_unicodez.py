# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
the worst file in the universe
"""

import pytest

from packit.utils.commands import run_command


def test_run_cmd_unicode(tmp_path):
    # don't ask me what this is, I took it directly from systemd's test suite
    # that's what packit was UnicodeDecodeError-ing on
    cancer = (
        b"\x06\xd0\xf1\t\x01\xa1\x01\t "
        b"\x15\x00&\xff\x00u\x08\x95@\x81\x02\t!\x15\x00&\xff\x00u\x08\x95@\x91\x02\xc0"
    )
    t = tmp_path / "the-cancer"
    t.write_bytes(cancer)
    command = ["cat", str(t)]
    assert cancer == run_command(command, decode=False, output=True)

    with pytest.raises(UnicodeDecodeError):
        run_command(command, decode=True, output=True)
