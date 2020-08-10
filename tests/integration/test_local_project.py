# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import subprocess
from pathlib import Path

from ogr import GithubService, GitlabService
from packit.local_project import LocalProject
from tests.spellbook import initiate_git_repo


def test_pr_id_and_ref(tmp_path: Path):
    """ p-s passes both ref and pr_id, we want to check out PR """
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=remote)
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

    LocalProject(
        working_dir=upstream_git,
        offline=True,
        pr_id=pr_id,
        ref=ref,
        git_service=GithubService(),
    )

    assert (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=upstream_git
        )
        .strip()
        .decode()
        == f"pr/{pr_id}"
    )


def test_pr_id_and_ref_gitlab(tmp_path: Path):
    """ p-s passes both ref and pr_id, we want to check out PR """
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=remote)
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

    LocalProject(
        working_dir=upstream_git,
        offline=True,
        pr_id=pr_id,
        ref=ref,
        git_service=GitlabService(token="12345"),
    )

    assert (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=upstream_git
        )
        .strip()
        .decode()
        == f"pr/{pr_id}"
    )
