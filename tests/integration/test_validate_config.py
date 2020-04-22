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

from packit.config import PackageConfig
from packit.exceptions import PackitConfigException
from packit.utils import cwd
from tests.spellbook import DATA_DIR


@pytest.mark.parametrize(
    "package_config,raw_package_config,contains",
    [
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome"
            }
            """,
            "packit.json is valid and ready to be used",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": 23,
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome"
            }
            """,
            "packit.json does not pass validation:\n"
            "* field downstream_package_name: Not a valid string.",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                create_pr: ""
            }
            """,
            "packit.json does not pass validation:\n* field create_pr: Not a valid boolean.",
        ),
    ],
)
def test_schema_validation_primitive_types(
    cwd_upstream, api_instance, package_config, raw_package_config, contains
):
    with cwd(DATA_DIR / "validate_config"):
        u, d, api = api_instance
        api.package_config = package_config

        with open("packit.json", "w") as package_config_file:
            package_config_file.writelines(raw_package_config)

        output = api.validate()
        assert contains in output


@pytest.mark.parametrize(
    "package_config,raw_package_config,contains",
    [
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https: //packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome"
            }
            """,
            "packit.json is valid and ready to be used",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https: //packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": "gpg",
                "dist_git_namespace": "awesome"
            }
            """,
            "packit.json does not pass validation:\n"
            "* field allowed_gpg_keys: Not a valid list.",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path":"packit.json",
                "dist_git_base_url":"https://packit.dev/",
                "downstream_package_name":"packit",
                "upstream_ref":"last_commit",
                "upstream_package_name":"packit_upstream",
                "create_tarball_command":[25],
                "allowed_gpg_keys":["gpg"],
                "dist_git_namespace":"awesome"
            }
            """,
            "packit.json does not pass validation:\n"
            "* field create_tarball_command has incorrect values:\n"
            "** value at index 0: Not a valid string.",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path":"packit.json",
                "dist_git_base_url":"https://packit.dev/",
                "downstream_package_name":"packit",
                "upstream_ref":"last_commit",
                "upstream_package_name":"packit_upstream",
                "create_tarball_command":["commands", True],
                "allowed_gpg_keys":["gpg"],
                "dist_git_namespace":"awesome"
            }
            """,
            "packit.json does not pass validation:\n"
            "* field create_tarball_command has incorrect values:\n"
            "** value at index 1: Not a valid string.",
        ),
    ],
)
def test_schema_validation_list_types(
    cwd_upstream, api_instance, package_config, raw_package_config, contains
):
    with cwd(DATA_DIR / "validate_config"):
        u, d, api = api_instance
        api.package_config = package_config

        with open("packit.json", "w") as package_config_file:
            package_config_file.writelines(raw_package_config)

        output = api.validate()
        assert contains in output


@pytest.mark.parametrize(
    "package_config,raw_package_config,contains",
    [
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "synced_files": {
                    "files_to_sync": ["a.md", "b.md", "c.txt"]
                }
            }
            """,
            "packit.json is valid and ready to be used",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "synced_files": {
                    "files_to_sync": [{ "src": 55, "dest": "a.md" }, "b.md", "c.txt"]
                }
            }
            """,
            "packit.json does not pass validation:\n"
            "* field synced_files has incorrect values:\n"
            "** field files_to_sync has incorrect values:\n"
            "*** value at index 0: Field `src` should have type str.",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "synced_files": {
                    "files_to_sync": ["a.md", "b.md", { "src": "c.txt", "dest": True }]
                }
            }
            """,
            "packit.json does not pass validation:\n"
            "* field synced_files has incorrect values:\n"
            "** field files_to_sync has incorrect values:\n"
            "*** value at index 2: Field `dest` should have type str.",
        ),
    ],
)
def test_schema_validation_synced_files(
    cwd_upstream, api_instance, package_config, raw_package_config, contains
):
    with cwd(DATA_DIR / "validate_config"):
        u, d, api = api_instance
        api.package_config = package_config

        with open("packit.json", "w") as package_config_file:
            package_config_file.writelines(raw_package_config)

        output = api.validate()
        assert contains in output


@pytest.mark.parametrize(
    "package_config,raw_package_config,contains",
    [
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "notifications": {
                    "pull_request": {
                        "successful_build": True
                    }
                }
            }
            """,
            "packit.json is valid and ready to be used",
        ),
        (
            PackageConfig(config_file_path="packit.json",),
            """
            {
                "config_file_path": "packit.json",
                "dist_git_base_url": "https://packit.dev/",
                "downstream_package_name": "packit",
                "upstream_ref": "last_commit",
                "upstream_package_name": "packit_upstream",
                "create_tarball_command": ["commands"],
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "notifications": {
                    "pull_request": {
                        "successful_build": 55
                    }
                }
            }
            """,
            "packit.json does not pass validation:\n"
            "* field notifications has incorrect values:\n"
            "** field pull_request has incorrect values:\n"
            "*** value at index successful_build: Not a valid boolean.",
        ),
    ],
)
def test_schema_validation_notifications(
    cwd_upstream, api_instance, package_config, raw_package_config, contains
):
    with cwd(DATA_DIR / "validate_config"):
        u, d, api = api_instance
        api.package_config = package_config

        with open("packit.json", "w") as package_config_file:
            package_config_file.writelines(raw_package_config)

        output = api.validate()
        assert contains in output


def test_schema_validation_config_name_missing(cwd_upstream, api_instance):
    with cwd(DATA_DIR / "validate_config"):
        u, d, api = api_instance
        api.package_config = PackageConfig()

        with open("packit.json", "w") as package_config_file:
            package_config_file.writelines("{}")
            try:
                api.validate()
            except PackitConfigException:
                assert True
            else:
                assert False
