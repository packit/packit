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
from datetime import datetime
from pathlib import Path

from ogr.services.pagure import PagureService
from vcr import use_cassette

from tests.spellbook import git_set_user_email


RESPONSE_HEADERS_TO_DROP = [
    "X-Fedora-RequestID",
    "content-security-policy",
    "set-cookie",
]


def drop_sensitive_response_data(response):
    for h in RESPONSE_HEADERS_TO_DROP:
        try:
            del response["headers"][h]
        except KeyError:
            pass
    return response


def test_basic_distgit_workflow(tmpdir):
    # if pagure_token is not set and we're recording, we'll get a token failure,
    # but that's expected so no need to take care of it
    with use_cassette(
        path=str(Path(__file__).parent / "test_basic_distgit_workflow"),
        filter_headers=["Authorization", "Cookie"],
        before_record_response=drop_sensitive_response_data,
    ) as cassette:
        # cassette.data is populated with pre-recorded data which are loaded from a local file
        # if there is no such file, it's empty and it implies we're recording
        replay_mode = bool(cassette.data)

        pagure_token = os.getenv("PAGURE_TOKEN")

        pag = PagureService(
            token=pagure_token, instance_url="https://src.stg.fedoraproject.org/",
        )

        assert pag.user.get_username()  # make sure the token is set

        proj = pag.get_project(repo="tmux-top", namespace="rpms",)

        fork = proj.get_fork(create=True)
        urls = fork.get_git_urls()
        if replay_mode:
            clone_url = urls["git"]
        else:  # record mode
            clone_url = urls["ssh"]

        t = Path(tmpdir)
        repo = t.joinpath("repo")

        branch_name = "cookie"

        subprocess.check_call(["git", "clone", clone_url, repo])
        git_set_user_email(repo)
        subprocess.check_call(["git", "checkout", "-B", branch_name], cwd=repo)
        subprocess.check_call(
            ["git", "pull", "--rebase", "origin", f"{branch_name}:{branch_name}"],
            cwd=repo,
        )

        now = datetime.now().strftime("%Y%m%d%H%M%S%f")
        repo.joinpath("README").write_text(f"just trying something out [{now}]\n")

        subprocess.check_call(["git", "add", "README"], cwd=repo)
        subprocess.check_call(["git", "commit", "-m", "test commit"], cwd=repo)
        if not replay_mode:
            # recording mode: push actually since we need to get the whole flow
            # replay mode: don't push (wouldn't have the perms in CI)
            subprocess.check_call(
                ["git", "push", "origin", f"{branch_name}:{branch_name}"], cwd=repo
            )

        pr = fork.pr_create("testing PR", "serious description", "master", branch_name)

        proj.pr_comment(pr.id, "howdy!")
