# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
                "allowed_gpg_keys": ["gpg"],
                "dist_git_namespace": "awesome",
                "synced_files": ["a.md", "b.md", "c.txt"]
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
                    "allowed_gpg_keys": ["gpg"],
                    "dist_git_namespace": "awesome",
                    "synced_files": [{ "src": 55, "dest": "a.md" }, "b.md", "c.txt"]
                }
                """,
            "Expected 'list[str]' or 'str', got <class 'int'>.",
        ),
        (
            """
                {
                    "config_file_path": "packit.json",
                    "dist_git_base_url": "https://packit.dev/",
                    "downstream_package_name": "packit",
                    "upstream_ref": "last_commit",
                    "upstream_package_name": "packit_upstream",
                    "allowed_gpg_keys": ["gpg"],
                    "dist_git_namespace": "awesome",
                    "synced_files": ["a.md", "b.md", { "src": "c.txt", "dest": True }]
                }
                """,
            "dest: Not a valid string.",
        ),
        (
            """
                {
                    "dist_git_base_url": "https://packit.dev/",
                    "downstream_package_name": "packit",
                    "upstream_ref": "last_commit",
                    "upstream_package_name": "packit_upstream",
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
                    "allowed_gpg_keys": "gpg",
                    "dist_git_namespace": "awesome"
                }
                """,
            "* field allowed_gpg_keys: Not a valid list.",
        ),
        (
            """
                {
                    "config_file_path": "packit.json",
                    "dist_git_base_url": "https: //packit.dev/",
                    "downstream_package_name": "packit",
                    "upstream_ref": "last_commit",
                    "upstream_package_name": "packit/upstream",
                    "allowed_gpg_keys": ["gpg"],
                    "dist_git_namespace": "awesome"
                }
                """,
            " Repository name must be a valid filename.",
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
        "slash_in_package_name",
    ],
)
def test_schema_validation(tmpdir, raw_package_config, expected_output):
    with cwd(tmpdir):
        Path("packit.json").write_text(raw_package_config)
        Path("packit.spec").write_text("hello")
        Path("a.md").write_text("a")
        Path("b.md").write_text("b")
        Path("c.txt").write_text("c")

        output = PackitAPI.validate_package_config(Path("."))
        assert expected_output in output
