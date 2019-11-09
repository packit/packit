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
from packit.utils import cwd
from tests.spellbook import DATA_DIR


@pytest.mark.parametrize(
    "packit_files,expected",
    [
        (
            SyncFilesConfig(files_to_sync=[SyncFilesItem(src="a.md", dest="a.md")]),
            [RawSyncFilesItem(Path("a.md"), Path("a.md"), False)],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="a.md", dest="a.md"),
                    SyncFilesItem(src="b.md", dest="b.md"),
                    SyncFilesItem(src="c.txt", dest="c.txt"),
                ]
            ),
            [
                RawSyncFilesItem(Path("a.md"), Path("a.md"), False),
                RawSyncFilesItem(Path("b.md"), Path("b.md"), False),
                RawSyncFilesItem(Path("c.txt"), Path("c.txt"), False),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="example_dir/", dest="tests")]
            ),
            [RawSyncFilesItem(Path("example_dir"), Path("tests"), False)],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="example_dir/*.md", dest="tests/")]
            ),
            [
                RawSyncFilesItem(Path("example_dir/d.md"), Path("tests"), True),
                RawSyncFilesItem(Path("example_dir/e.md"), Path("tests"), True),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="example_dir/e*d", dest="example")]
            ),
            [RawSyncFilesItem(Path("example_dir/e.md"), Path("example"), False)],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(
                        src=["example_dir/d.md", "example_dir/e.md"], dest="tests"
                    )
                ]
            ),
            [
                RawSyncFilesItem(Path("example_dir/d.md"), Path("tests"), False),
                RawSyncFilesItem(Path("example_dir/e.md"), Path("tests"), False),
            ],
        ),
    ],
)
def test_raw_files_to_sync(packit_files, expected):
    with cwd(DATA_DIR / "sync_files"):
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
