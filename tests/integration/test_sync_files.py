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

import pytest

from packit.config import PackageConfig, SyncFilesItem, SyncFilesConfig

from packit.sync import get_wildcard_resolved_sync_files
from tests.spellbook import TESTS_DIR
from tests.utils import cwd


@pytest.mark.parametrize(
    "packit_files,expected",
    [
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="conftest.py", dest="conftest.py")]
            ),
            [SyncFilesItem(src="conftest.py", dest="conftest.py")],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="__init__.py", dest="__init__.py"),
                    SyncFilesItem(src="conftest.py", dest="conftest.py"),
                    SyncFilesItem(src="spellbook.py", dest="spellbook.py"),
                ]
            ),
            [
                SyncFilesItem(src="__init__.py", dest="__init__.py"),
                SyncFilesItem(src="conftest.py", dest="conftest.py"),
                SyncFilesItem(src="spellbook.py", dest="spellbook.py"),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/", dest="tests")]
            ),
            [
                SyncFilesItem(src="data/sync_files/a.md", dest="tests"),
                SyncFilesItem(src="data/sync_files/b.md", dest="tests"),
                SyncFilesItem(src="data/sync_files/c.txt", dest="tests"),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/*.md", dest="tests")]
            ),
            [
                SyncFilesItem(src="data/sync_files/a.md", dest="tests"),
                SyncFilesItem(src="data/sync_files/b.md", dest="tests"),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/b*d", dest="example")]
            ),
            [SyncFilesItem(src="data/sync_files/b.md", dest="example")],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(
                        src=["data/sync_files/a.md", "data/sync_files/b.md"],
                        dest="tests",
                    )
                ]
            ),
            [
                SyncFilesItem(src="data/sync_files/a.md", dest="tests"),
                SyncFilesItem(src="data/sync_files/b.md", dest="tests"),
            ],
        ),
    ],
)
def test_sync_files(packit_files, expected):
    with cwd(TESTS_DIR):
        pc = PackageConfig(
            dist_git_base_url="https://packit.dev/",
            downstream_package_name="packit",
            dist_git_namespace="awesome",
            specfile_path="fedora/package.spec",
            synced_files=packit_files,
        )
        synced_files = get_wildcard_resolved_sync_files(pc)
        assert set(synced_files) == set(expected)
