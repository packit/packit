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
from shutil import copy

import pytest
from rebasehelper.specfile import SpecContent

from packit.specfile import Specfile
from tests.spellbook import SPECFILE, UP_OSBUILD, UP_EDD, UP_VSFTPD


def test_write_spec_content():
    with open(SPECFILE) as spec:
        content = spec.read()

    data = "new line 1\n"
    spec = Specfile(SPECFILE)
    spec.spec_content.replace_section("%description", [data])
    spec.write_spec_content()

    with open(SPECFILE) as specfile:
        assert "new line 1" in specfile.read()
        spec.spec_content = SpecContent(content)
        spec.write_spec_content()


@pytest.mark.parametrize(
    "input_spec",
    [
        UP_VSFTPD / "Fedora" / "vsftpd.spec",
        UP_OSBUILD / "osbuild.spec",
        UP_EDD / "edd.spec",
    ],
)
def test_ensure_pnum(tmp_path, input_spec):
    spec = Path(copy(input_spec, tmp_path))
    Specfile(spec).ensure_pnum()
    text = spec.read_text()
    assert "%autosetup -p1" in text
    # %autosetup does not accept -q
    assert "-q" not in text
