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

from packit.config.package_config import PackageConfigValidation

from packit.config import PackageConfig, SyncFilesItem, SyncFilesConfig
from packit.utils import cwd
from tests.spellbook import DATA_DIR


@pytest.mark.parametrize(
    "packit_config,contains",
    [
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="beer.spec", dest="beer.spec")]
                ),
            ),
            "'specfile_path validation errors: ['packit.spec file does not exist']''",
        ),
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                specfile_path="beer.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="beer.spec", dest="beer.spec")]
                ),
            ),
            "'config_file_path validation errors: ['Field may not be null.']'",
        ),
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                specfile_path="beer.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(src="a.md", dest="a.md"),
                        SyncFilesItem(src="b.md", dest="b.md"),
                        SyncFilesItem(src="c.txt", dest="c.txt"),
                    ]
                ),
            ),
            "'config_file_path validation errors: ['Field may not be null.']'",
        ),
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="not_existing",
                dist_git_namespace="awesome",
                specfile_path="beer.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(src="a.md", dest="a.md"),
                        SyncFilesItem(src="b.md", dest="b.md"),
                        SyncFilesItem(src="c.txt", dest="c.txt"),
                    ]
                ),
            ),
            "Downstream package not_existing does not exist",
        ),
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                specfile_path="not_existing.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(src="a.md", dest="a.md"),
                        SyncFilesItem(src="b.md", dest="b.md"),
                        SyncFilesItem(src="c.txt", dest="c.txt"),
                    ]
                ),
            ),
            "not_existing.spec file does not exist",
        ),
        (
            PackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                specfile_path="beer.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(src="a.md", dest="a.md"),
                        SyncFilesItem(src="not_existing.md", dest="not_existing.md"),
                        SyncFilesItem(src="c.txt", dest="c.txt"),
                    ]
                ),
            ),
            "not_existing.md file does not exist",
        ),
    ],
)
def test_config_validation(packit_config, contains):
    with cwd(DATA_DIR / "config_validation"):
        validator = PackageConfigValidation(packit_config)
        assert str(validator).find(contains)
