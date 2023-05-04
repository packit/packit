# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from packit.api import PackitAPI
from packit.exceptions import PackitConfigException
from packit.utils.commands import cwd


@pytest.mark.parametrize(
    "existing_files,existing_directories,raw_package_config,valid,expected_output",
    [
        (
            ["a.md", "b.md"],
            ["./a_dir"],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- src: a.md
  dest: aaa.md
- a_dir
            """,
            True,
            ".packit.yaml is valid and ready to be used",
        ),
        (
            ["a.md", "b.md"],
            ["./a_dir"],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- a.md
- b.md
- c.txt
- a_dir
            """,
            False,
            "The following path is configured to be synced but is not present "
            "in the repository: c.txt",
        ),
        (
            ["a.md"],
            [],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- a.md
- b.md
- c.txt
            """,
            False,
            "The following paths are configured to be synced but are not present "
            "in the repository: b.md, c.txt",
        ),
        (
            ["a.md", "./a_dir/file"],
            ["./a_dir"],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- a.md
- b.md
- c.txt
- ./a_dir/*
            """,
            False,
            "The following paths are configured to be synced but are not present "
            "in the repository: b.md, c.txt",
        ),
        (
            ["a.md", "b.md"],
            ["./a_dir"],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- ./a_dir/*
- a.md
- b.md
- c.txt
            """,
            False,
            "The following paths are configured to be synced but are not present "
            "in the repository: ./a_dir/*, c.txt",
        ),
        (
            ["a.md", "b.md"],
            ["./a_dir"],
            """\
config_file_path: .packit.yaml
dist_git_base_url: https://packit.dev/
downstream_package_name: packit
upstream_ref: last_commit
upstream_package_name: packit_upstream
allowed_gpg_keys:
- gpg
dist_git_namespace: awesome
files_to_sync:
- .packit.yaml
- packit.spec
- ./a_dir
- a.md
- b.md
            """,
            True,
            ".packit.yaml is valid and ready to be used",
        ),
    ],
    ids=[
        "none_missing",
        "one_missing",
        "two_missing",
        "dir_with_globs",
        "empty_dir_with_globs",
        "empty_dir",
    ],
)
def test_validate_paths(
    tmpdir,
    existing_files,
    existing_directories,
    raw_package_config,
    valid,
    expected_output,
):
    with cwd(tmpdir):
        Path(".packit.yaml").write_text(raw_package_config)
        Path("packit.spec").write_text("hello")
        for existing_directory in existing_directories:
            Path(existing_directory).mkdir()
        for existing_file in existing_files:
            Path(existing_file).write_text("")

        if valid:
            output = PackitAPI.validate_package_config(Path("."))
            assert expected_output in output
        else:
            with pytest.raises(PackitConfigException) as exc:
                PackitAPI.validate_package_config(Path("."))
                assert expected_output in exc
