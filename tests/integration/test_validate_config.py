# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

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

from packit.api import PackitAPI
from packit.utils.commands import cwd


@pytest.mark.parametrize(
    "raw_package_config,expected_output",
    [
        (
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
            "* field notifications has an incorrect value:\n"
            "** field pull_request has an incorrect value:\n"
            "*** value at index successful_build: Not a valid boolean.",
        ),
        ("{}", "packit.json is valid and ready to be used"),
        (
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
            "* field synced_files has an incorrect value:\n"
            "** field files_to_sync has an incorrect value:\n"
            "*** value at index 0: Field `src` should have type str.",
        ),
        (
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
            "* field synced_files has an incorrect value:\n"
            "** field files_to_sync has an incorrect value:\n"
            "*** value at index 2: Field `dest` should have type str.",
        ),
        (
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
            "* field downstream_package_name: Not a valid string.",
        ),
        (
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
            "* field create_pr: Not a valid boolean.",
        ),
        (
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
            "* field allowed_gpg_keys: Not a valid list.",
        ),
        (
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
            "* field create_tarball_command has an incorrect value:\n"
            "** value at index 0: Not a valid string.",
        ),
        (
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
            "* field create_tarball_command has an incorrect value:\n"
            "** value at index 1: Not a valid string.",
        ),
    ],
    ids=[
        "valid_1",
        "notif_succ_build",
        "empty",
        "valid_2",
        "synced_files_src",
        "synced_files_dest",
        "valid_3",
        "downstream_name",
        "create_pr",
        "valid_4",
        "allowed_gpg",
        "create_tarball_1",
        "create_tarball_2",
    ],
)
def test_schema_validation(tmpdir, raw_package_config, expected_output):
    with cwd(tmpdir):
        Path("packit.json").write_text(raw_package_config)
        Path("packit.spec").write_text("hello")

        output = PackitAPI.validate_package_config(Path("."))
        assert expected_output in output
