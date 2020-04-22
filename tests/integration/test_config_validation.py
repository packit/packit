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
from packit.sync import SyncFilesItem

from packit.config.sync_files_config import SyncFilesConfig

from packit.config import PackageConfig
from packit.config.package_config import PackageConfigValidationValues
from packit.utils import cwd
from tests.spellbook import DATA_DIR


@pytest.mark.parametrize(
    "package_config,contains",
    [
        (
            PackageConfig(
                config_file_path="packit.yml",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
            ),
            ".packit.yaml is valid and ready to be used",
        ),
        (
            PackageConfig(
                config_file_path="packit.yml",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="not_existing",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
                dist_git_namespace="awesome",
            ),
            "* there is no such downstream package - not_existing",
        ),
        (
            PackageConfig(
                config_file_path="packit.yml",
                specfile_path="beer.spec",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
                dist_git_namespace="awesome",
            ),
            ".packit.yaml is valid and ready to be used",
        ),
        (
            PackageConfig(
                config_file_path="packit.yml",
                specfile_path="not_existing",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
                dist_git_namespace="awesome",
            ),
            "* specfile_path: not_existing does not exist",
        ),
        (
            PackageConfig(
                config_file_path="packit.yml",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
                dist_git_namespace="awesome",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="a.md", dest="a.md")]
                ),
            ),
            ".packit.yaml is valid and ready to be used",
        ),
        (
            PackageConfig(
                config_file_path="packit.yml",
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                upstream_ref="last_commit",
                upstream_package_name="packit_upstream",
                create_tarball_command=["commands"],
                allowed_gpg_keys=["gpg"],
                dist_git_namespace="awesome",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="a.md", dest="not_existing.md")]
                ),
            ),
            "* synced_files: not_existing.md does not exist",
        ),
    ],
)
def test_schema_validation_values(package_config, contains):
    with cwd(DATA_DIR / "package_config_validation"):
        validator = PackageConfigValidationValues(package_config)
        assert contains in str(validator)
