# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock
from ogr import GithubService, GitlabService

from packit.local_project import LocalProject
from packit.utils.repo import create_new_repo
from tests.spellbook import initiate_git_repo


@pytest.mark.parametrize(
    "merge, hops_file_content",
    ((True, "Cascade\n"), (False, None)),
)
def test_pr_id_and_ref(tmp_path: Path, merge, hops_file_content):
    """p-s passes both ref and pr_id, we want to check out PR"""
    remote = tmp_path / "remote"
    remote.mkdir()
    create_new_repo(remote, ["--bare"])
    upstream_git = tmp_path / "upstream_git"
    upstream_git.mkdir()
    initiate_git_repo(upstream_git, push=True, upstream_remote=str(remote))
    # mimic github PR
    pr_id = "123"
    ref = (
        subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=upstream_git)
        .strip()
        .decode()
    )
    local_tmp_branch = "asdqwe"
    subprocess.check_call(["git", "branch", local_tmp_branch, ref], cwd=upstream_git)
    subprocess.check_call(
        ["git", "push", "origin", f"{local_tmp_branch}:refs/pull/{pr_id}/head"],
        cwd=upstream_git,
    )
    subprocess.check_call(["git", "branch", "-D", local_tmp_branch], cwd=upstream_git)

    git_project = flexmock(repo="random_name", namespace="random_namespace")
    git_project.should_receive("get_pr").and_return(flexmock(target_branch="main"))

    LocalProject(
        working_dir=upstream_git,
        offline=True,
        pr_id=pr_id,
        ref=ref,
        git_service=GithubService(),
        git_project=git_project,
        merge_pr=merge,
    )

    assert (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=upstream_git,
        )
        .strip()
        .decode()
        == f"pr/{pr_id}"
    )
    if hops_file_content:
        # the changes are merged into main so the file should be there
        assert (upstream_git / "hops").read_text() == hops_file_content
    else:
        # we haven't merged into main, so there should be no "hops" file
        assert not (upstream_git / "hops").is_file()


def test_pr_id_and_ref_gitlab(tmp_path: Path):
    """p-s passes both ref and pr_id, we want to check out PR"""
    remote = tmp_path / "remote"
    remote.mkdir()
    create_new_repo(remote, ["--bare"])
    upstream_git = tmp_path / "upstream_git"
    upstream_git.mkdir()
    initiate_git_repo(upstream_git, push=True, upstream_remote=str(remote))
    # mimic gitlab MR
    pr_id = "123"
    ref = (
        subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=upstream_git)
        .strip()
        .decode()
    )
    local_tmp_branch = "asdqwe"
    subprocess.check_call(["git", "branch", local_tmp_branch, ref], cwd=upstream_git)
    subprocess.check_call(
        [
            "git",
            "push",
            "origin",
            f"{local_tmp_branch}:refs/merge-requests/{pr_id}/head",
        ],
        cwd=upstream_git,
    )
    subprocess.check_call(["git", "branch", "-D", local_tmp_branch], cwd=upstream_git)

    git_project = flexmock(repo="random_name", namespace="random_namespace")
    git_project.should_receive("get_pr").and_return(flexmock(target_branch="main"))

    LocalProject(
        working_dir=upstream_git,
        offline=True,
        pr_id=pr_id,
        ref=ref,
        git_service=GitlabService(token="12345"),
        git_project=git_project,
    )

    assert (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=upstream_git,
        )
        .strip()
        .decode()
        == f"pr/{pr_id}"
    )
