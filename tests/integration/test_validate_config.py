# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from textwrap import dedent

import pytest

from packit.api import PackitAPI
from packit.exceptions import PackitConfigException
from packit.utils.commands import cwd


@pytest.mark.parametrize(
    "raw_package_config,valid, expected_output",
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
            """,
            ),
            True,
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
            """,
            ),
            False,
            "value at index successful_build: Not a valid boolean.",
        ),
        ("", True, "packit.yaml is valid and ready to be used"),
        (
            dedent(
                """\
                dist_git_base_url: https://packit.dev/
                downstream_package_name: packit
                upstream_ref: last_commit
                upstream_package_name: packit_upstream
                allowed_gpg_keys: [gpg]
                dist_git_namespace: awesome
                files_to_sync:
                - a.md
                - b.md
                - c.txt
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches: fedora-latest
            """,
            ),
            True,
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
                files_to_sync:
                - src: 55
                  dest: a.md
                - b.md
                - c.txt
            """,
            ),
            False,
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
                files_to_sync:
                - a.md
                - b.md
                - src: c.txt
                  dest: True
            """,
            ),
            False,
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
            """,
            ),
            True,
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
            """,
            ),
            False,
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
            """,
            ),
            False,
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
            """,
            ),
            True,
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                downstream_package_name: packit
                upstream_package_name: packit_upstream
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches:
                    fedora-rawhide:
                      fast_forward_merge_into: [fedora-all]
            """,
            ),
            True,
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                downstream_package_name: packit
                upstream_package_name: packit_upstream
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches:
                    fedora-rawhide:
                      fast_forward_merge_into: [f40]
                    f40:
                      fast_forward_merge_into: [f39]
            """,
            ),
            True,
            "packit.yaml is valid and ready to be used",
        ),
        (
            dedent(
                """\
                downstream_package_name: packit
                upstream_package_name: packit_upstream
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches:
                    fedora-rawhide:
                      f40
            """,
            ),
            False,
            "Expected 'list[str]' or 'dict[str, dict[str, list]]'",
        ),
        (
            dedent(
                """\
                downstream_package_name: packit
                upstream_package_name: packit_upstream
                jobs:
                - job: propose_downstream
                  trigger: release
                  dist_git_branches:
                    fedora-rawhide:
                      open_pull_request: f40
            """,
            ),
            False,
            'Example -> "dist_git_branches":'
            ' {"fedora-rawhide": {"fast_forward_merge_into": ["f40"]}, epel9: {}}}',
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
            """,
            ),
            False,
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
            """,
            ),
            False,
            " Repository name must be a valid filename.",
        ),
    ],
    ids=[
        "valid_1",
        "notif_succ_build",
        "empty",
        "valid_2",
        "files_to_sync_src",
        "files_to_sync_dest",
        "valid_3",
        "downstream_name",
        "create_pr",
        "valid_4",
        "one_mapping_dist_git_prs",
        "multiple_mappings_dist_git_prs",
        "missing_fast_forward_merge_into_key",
        "wrong_fast_forward_merge_into_key",
        "allowed_gpg",
        "slash_in_package_name",
    ],
)
def test_schema_validation(tmpdir, raw_package_config, valid, expected_output):
    with cwd(tmpdir):
        Path("test_dir").mkdir()
        Path("test_dir/packit.yaml").write_text(raw_package_config)
        Path("test_dir/packit.spec").write_text("hello")
        Path("test_dir/a.md").write_text("a")
        Path("test_dir/b.md").write_text("b")
        Path("test_dir/c.txt").write_text("c")

        if valid:
            output = PackitAPI.validate_package_config(Path("test_dir"))
            assert expected_output in output
        else:
            with pytest.raises(PackitConfigException) as exc_info:
                PackitAPI.validate_package_config(Path("test_dir"))
            assert expected_output in str(exc_info.value)
