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

from packit.config import PackageConfig, SyncFilesItem, SyncFilesConfig
from packit.sync import RawSyncFilesItem
from tests.spellbook import TESTS_DIR
from packit.utils import cwd


@pytest.mark.parametrize(
    "packit_files,expected",
    [
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="conftest.py", dest="conftest.py")]
            ),
            [RawSyncFilesItem(Path("conftest.py"), Path("conftest.py"), False)],
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
                RawSyncFilesItem(Path("__init__.py"), Path("__init__.py"), False),
                RawSyncFilesItem(Path("conftest.py"), Path("conftest.py"), False),
                RawSyncFilesItem(Path("spellbook.py"), Path("spellbook.py"), False),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/", dest="tests")]
            ),
            [RawSyncFilesItem(Path("data/sync_files"), Path("tests"), False)],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/*.md", dest="tests/")]
            ),
            [
                RawSyncFilesItem(Path("data/sync_files/a.md"), Path("tests"), True),
                RawSyncFilesItem(Path("data/sync_files/b.md"), Path("tests"), True),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="data/sync_files/b*d", dest="example")]
            ),
            [RawSyncFilesItem(Path("data/sync_files/b.md"), Path("example"), False)],
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
                RawSyncFilesItem(Path("data/sync_files/a.md"), Path("tests"), False),
                RawSyncFilesItem(Path("data/sync_files/b.md"), Path("tests"), False),
            ],
        ),
    ],
)
def test_raw_files_to_sync(packit_files, expected):
    with cwd(TESTS_DIR):
        pc = PackageConfig(
            dist_git_base_url="https://packit.dev/",
            downstream_package_name="packit",
            dist_git_namespace="awesome",
            specfile_path="fedora/package.spec",
            synced_files=packit_files,
        )
        assert set(pc.synced_files.get_raw_files_to_sync(Path("."), Path("."))) == set(
            expected
        )
