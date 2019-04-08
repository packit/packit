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

import copy
import git
import pytest
from flexmock import flexmock
from git import Repo
from rebasehelper.specfile import SpecFile

from packit.api import PackitAPI
from packit.bot_api import PackitBotAPI
from packit.config import get_local_package_config
from packit.fed_mes_consume import Consumerino
from packit.local_project import LocalProject
from tests.spellbook import TARBALL_NAME, get_test_config
from tests.utils import cwd


@pytest.fixture()
def github_release_fedmsg():
    return {
        "msg_id": "2019-a5034b55-339d-4fa5-a72b-db74579aeb5a",
        "topic": "org.fedoraproject.prod.github.release",
        "msg": {
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
        },
    }


def test_basic_local_update(upstream_n_distgit, mock_upstream_remote_functionality):
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
        spec = SpecFile(str(d / "beer.spec"), None)
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
        spec = SpecFile(str(u / "beer.spec"), None)
        assert spec.get_version() == "0.0.0"


def test_single_message(github_release_fedmsg, mock_upstream_remote_functionality):
    u, d = mock_upstream_remote_functionality

    conf = get_test_config()
    api = PackitBotAPI(conf)

    flexmock(Repo).should_receive("clone_from").and_return(git.Repo(str(u)))

    api.sync_upstream_release_with_fedmsg(github_release_fedmsg)
    assert (d / TARBALL_NAME).is_file()
    spec = SpecFile(str(d / "beer.spec"), None)
    assert spec.get_version() == "0.1.0"


def test_loop(mock_upstream_remote_functionality, github_release_fedmsg):
    u, d = mock_upstream_remote_functionality

    def mocked_iter_releases():
        msg = copy.deepcopy(github_release_fedmsg)
        yield msg["topic"], msg

    flexmock(Repo).should_receive("clone_from").and_return(git.Repo(str(u)))
    flexmock(Consumerino, iterate_releases=mocked_iter_releases)
    conf = get_test_config()
    api = PackitBotAPI(conf)
    api.watch_upstream_release()
