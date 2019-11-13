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

import os
import subprocess
from pathlib import Path

import pytest
from ogr.services.pagure import PagureService

from tests.spellbook import git_set_user_email


@pytest.mark.skipif(
    condition=True, reason="Don't interact with a real pagure instance by default"
)
def test_basic_distgit_workflow(tmpdir):
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

    t = Path(tmpdir)
    repo = t.joinpath("repo")

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

    pr = fork.pr_create("testing PR", "serious description", "master", branch_name)

    proj.pr_comment(pr.id, "howdy!")
