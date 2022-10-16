# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from textwrap import dedent

import pytest

from packit.api import PackitAPI
from packit.utils.commands import cwd


@pytest.mark.parametrize(
    "raw_package_config,expected_output",
    [
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                notifications:
                    pull_request:
                        successful_build: true
                jobs:
                - job: copr_build
                  trigger: pull_request
                  targets: fedora-stable
            """
            ),
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                notifications:
                    pull_request:
                        successful_build: 55
            """
            ),
            "**** field notifications has an incorrect value:\n"
            "***** field pull_request has an incorrect value:\n"
            "****** value at index successful_build: Not a valid boolean.",
        ),
        ("", "packit.yaml is valid and ready to be used"),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                synced_files:
                - a.md
                - b.md
                - c.txt
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches: fedora-latest
            """
            ),
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                synced_files:
                - src: 55
                  dest: a.md
                - b.md
                - c.txt
            """
            ),
            "Expected 'list[str]' or 'str', got <class 'int'>.",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                synced_files:
                - a.md
                - b.md
                - src: c.txt
                  dest: True
            """
            ),
            "dest: Not a valid string.",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                jobs:
                - job: tests
                  trigger: pull_request
                  targets:
                  - fedora-stable
                  - centos-stream-9
            """
            ),
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: 23
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
            """
            ),
            "downstream_package_name: Not a valid string.",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                create_pr: ""
            """
            ),
            "create_pr: Not a valid boolean.",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                jobs:
                - job: bodhi_update
                  trigger: commit
                  dist_git_branches:
                  - f35
                  - f36
            """
            ),
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: gpg
                dist_git_namespace: awesome
            """
            ),
            "allowed_gpg_keys: Not a valid list.",
        ),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit/upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
            """
            ),
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
        Path("test_dir").mkdir()
        Path("test_dir/packit.yaml").write_text(raw_package_config)
        Path("test_dir/packit.spec").write_text("hello")
        Path("test_dir/a.md").write_text("a")
        Path("test_dir/b.md").write_text("b")
        Path("test_dir/c.txt").write_text("c")

        output = PackitAPI.validate_package_config(Path("test_dir"))
        assert expected_output in output
