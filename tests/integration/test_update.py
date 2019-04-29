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
import pytest
from flexmock import flexmock
from github import Github
from github.Repository import Repository
from ogr.services.github import GithubProject

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.jobs import SteveJobs
from packit.local_project import LocalProject
from tests.spellbook import TARBALL_NAME, get_test_config
from tests.utils import get_specfile
from packit.utils import cwd


@pytest.fixture()
def github_release_webhook():
    return {
        "repository": {
            "full_name": "brewery/beer",
            "owner": {"login": "brewery"},
            "name": "beer",
            "html_url": "https://github.com/brewery/beer",
        },
        "release": {
            "body": "Changelog content will be here",
            "tag_name": "0.1.0",
            "created_at": "2019-02-28T18:48:27Z",
            "published_at": "2019-02-28T18:51:10Z",
            "draft": False,
            "prerelease": False,
            "name": "Beer 0.1.0 is gooooood",
        },
        "action": "published",
    }


def test_basic_local_update(upstream_n_distgit, mock_remote_functionality_upstream):
    """ basic propose-update test: mock remote API, use local upstream and dist-git """
    u, d = upstream_n_distgit

    with cwd(u):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        pc.downstream_project_url = str(d)
        up_lp = LocalProject(path_or_url=str(u))
        api = PackitAPI(c, pc, up_lp)
        api.sync_release("master", "0.1.0")

        assert (d / TARBALL_NAME).is_file()
        spec = get_specfile(str(d / "beer.spec"))
        assert spec.get_version() == "0.1.0"


def test_basic_local_update_from_downstream(
    downstream_n_distgit, mock_downstream_remote_functionality
):
    flexmock(LocalProject, _parse_namespace_from_git_url=lambda: None)
    u, d = downstream_n_distgit

    with cwd(u):
        c = get_test_config()
        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        pc.downstream_project_url = str(d)
        up_lp = LocalProject(path_or_url=str(u))
        api = PackitAPI(c, pc, up_lp)
        api.sync_from_downstream("master", "master", True)

        assert (u / "beer.spec").is_file()
        spec = get_specfile(str(u / "beer.spec"))
        assert spec.get_version() == "0.0.0"


def test_single_message(github_release_webhook, mock_remote_functionality_upstream):
    u, d = mock_remote_functionality_upstream

    conf = get_test_config()
    steve = SteveJobs(conf)

    flexmock(GithubProject).should_receive("get_file_content").and_return(
        u.joinpath(".packit.json").read_text()
    )
    flexmock(Github, get_repo=Repository(None, None, {}, None))

    steve.process_message(github_release_webhook)
