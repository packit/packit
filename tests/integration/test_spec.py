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

import locale
import shutil
import tempfile

from rebasehelper.specfile import SpecContent

from packit.specfile import Specfile
from tests.spellbook import SPECFILE


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


def test_changelog_non_c_locale():
    (fd, specfile) = tempfile.mkstemp(prefix="packittest", suffix=".spec")
    shutil.copyfile(SPECFILE, specfile)
    spec = Specfile(specfile)
    spec.update_changelog_in_spec("test log")
    content = str(spec.spec_content)
    assert "test log" in content

    # Changelogs should be identical no matter what locale
    compared = False
    for loc in locale.locale_alias:
        try:
            locale.setlocale(locale.LC_TIME, loc)
            # Prevents us from trying out strange locale aliases that fail
            locale.setlocale(locale.LC_TIME, locale.getlocale(locale.LC_TIME))
        except locale.Error:
            continue
        shutil.copyfile(SPECFILE, specfile)
        spec = Specfile(specfile)
        spec.update_changelog_in_spec("test log")
        assert content == str(spec.spec_content)
        compared = True
    assert compared
