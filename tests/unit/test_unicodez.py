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
