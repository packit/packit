# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import os
import subprocess

import pytest
from ogr.services.pagure import PagureService

from tests.spellbook import git_set_user_email


@pytest.mark.skipif(
    condition=True, reason="Don't interact with a real pagure instance by default"
)
def test_basic_distgit_workflow(tmp_path):
    pagure_token = os.getenv("PAGURE_TOKEN")

    pag = PagureService(
        token=pagure_token,
        repo="tmux-top",
        namespace="rpms",
        instance_url="https://src.stg.fedoraproject.org/",
    )

    print(pag.pagure.whoami())

    proj = pag.get_project()

    fork = proj.get_fork(create=True)
    clone_url = fork.get_git_urls()["ssh"]

    repo = tmp_path.joinpath("repo")

    branch_name = "cookie"

    subprocess.check_call(["git", "clone", clone_url, repo])
    git_set_user_email(repo)
    subprocess.check_call(["git", "checkout", "-B", branch_name], cwd=repo)

    repo.joinpath("README").write_text("just trying something out\n")

    subprocess.check_call(["git", "add", "README"], cwd=repo)
    subprocess.check_call(["git", "commit", "-m", "test commit"], cwd=repo)
    subprocess.check_call(
        ["git", "push", "origin", f"{branch_name}:{branch_name}"], cwd=repo
    )

    pr = fork.create_pr("testing PR", "serious description", "master", branch_name)

    pr.comment("howdy!")
