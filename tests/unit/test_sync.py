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

import glob

import pytest
from flexmock import flexmock

from packit.config import SyncFilesConfig
from packit.sync import get_files_from_wildcard, get_raw_files, SyncFilesItem


@pytest.mark.parametrize(
    "file,glob_files,result",
    [
        ("file", ["file"], [SyncFilesItem(src="file", dest="dest")]),
        (
            "file/",
            ["file/a", "file/b"],
            [
                SyncFilesItem(src="file/a", dest="dest"),
                SyncFilesItem(src="file/b", dest="dest"),
            ],
        ),
        (
            "*.md",
            ["a.md", "b.md"],
            [
                SyncFilesItem(src="a.md", dest="dest"),
                SyncFilesItem(src="b.md", dest="dest"),
            ],
        ),
    ],
)
def test_get_files_from_wildcard(file, glob_files, result):
    flexmock(glob, glob=lambda x: glob_files)

    files = get_files_from_wildcard(file_wildcard=file, destination="dest")
    assert files == result


@pytest.mark.parametrize(
    "file,glob_files,result",
    [
        (
            SyncFilesItem(src="file/*", dest="dest"),
            ["file/a", "file/b"],
            [
                SyncFilesItem(src="file/a", dest="dest"),
                SyncFilesItem(src="file/b", dest="dest"),
            ],
        ),
        (
            SyncFilesItem(src=["*.md"], dest="dest"),
            ["a.md", "b.md"],
            [
                SyncFilesItem(src="a.md", dest="dest"),
                SyncFilesItem(src="b.md", dest="dest"),
            ],
        ),
    ],
)
def test_get_raw_files(file, glob_files, result):
    flexmock(glob, glob=lambda x: glob_files)

    files = get_raw_files(file_to_sync=file)
    assert files == result


def test_raw_files_to_sync():
    files_to_sync = SyncFilesConfig(files_to_sync=[]).raw_files_to_sync
    assert files_to_sync == []
