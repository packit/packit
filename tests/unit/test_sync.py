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

import pytest
from flexmock import flexmock

from packit.sync import get_raw_files, SyncFilesItem, RawSyncFilesItem


@pytest.mark.parametrize(
    "file,glob_files,result",
    [
        (
            SyncFilesItem(src="file/*", dest="dest"),
            [Path("file/a"), Path("file/b")],
            [
                RawSyncFilesItem(Path("file/a"), Path("dest"), False),
                RawSyncFilesItem(Path("file/b"), Path("dest"), False),
            ],
        ),
        (
            SyncFilesItem(src="file/*", dest="dest/"),
            [Path("file/a"), Path("file/b")],
            [
                RawSyncFilesItem(Path("file/a"), Path("dest"), True),
                RawSyncFilesItem(Path("file/b"), Path("dest"), True),
            ],
        ),
        (
            SyncFilesItem(src=["a"], dest="dest/"),
            [Path("a")],
            [RawSyncFilesItem(Path("a"), Path("dest"), True)],
        ),
        (
            SyncFilesItem(src=["*.md"], dest="dest"),
            [Path("a.md"), Path("b.md")],
            [
                RawSyncFilesItem(Path("a.md"), Path("dest"), False),
                RawSyncFilesItem(Path("b.md"), Path("dest"), False),
            ],
        ),
    ],
)
def test_get_raw_files(file, glob_files, result):
    flexmock(Path, glob=lambda x: glob_files)

    files = get_raw_files(Path("."), Path("."), file)
    assert files == result
