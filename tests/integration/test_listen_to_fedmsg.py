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
import git
import pytest
from flexmock import flexmock
from git import Repo
from ogr.services.pagure import PagureProject

from packit.jobs import SteveJobs
from tests.spellbook import get_test_config


@pytest.fixture()
def distgit_commit_fedmsg():
    return {
        "username": "ttomecek",
        "msg_id": "2019-ef06e723-1df2-41d1-9666-63ea1dc402d8",
        "topic": "org.fedoraproject.prod.git.receive",
        "msg": {
            "commit": {
                "rev": "e45f51fd481039a8f527451944a2feb4816ccebc",
                "namespace": "rpms",
                "summary": "packit: s/fedora/fedora-tests/",
                "repo": "packit",
                "branch": "master",
                "path": "/srv/git/repositories/rpms/packit.git",
                "message": (
                    "packit: s/fedora/fedora-tests/\n\n"
                    "Signed-off-by: Tomas Tomecek <ttomecek@redhat.com>\n"
                ),
                "email": "ttomecek@redhat.com",
            }
        },
    }


def test_distgit_commit_event(
    distgit_commit_fedmsg, mock_remote_functionality_upstream
):
    u, d = mock_remote_functionality_upstream

    conf = get_test_config()
    steve = SteveJobs(conf)

    flexmock(PagureProject).should_receive("get_file_content").and_return(
        u.joinpath(".packit.json").read_text()
    )
    flexmock(Repo).should_receive("clone_from").and_return(git.Repo(str(u)))

    steve.process_message(distgit_commit_fedmsg)
