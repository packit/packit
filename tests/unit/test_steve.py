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

"""
Let's test that Steve as awesome as we think he is.
"""
import pytest
from flexmock import flexmock
from github import Github
from ogr.services.github import GithubProject

from packit.api import PackitAPI
from packit.config import Config
from packit.jobs import SteveJobs
from packit.local_project import LocalProject


@pytest.mark.parametrize(
    "event",
    (
        (
            {
                "action": "published",
                "release": {"tag_name": "1.2.3"},
                "repository": {
                    "name": "bar",
                    "html_url": "https://github.com/foo/bar",
                    "owner": {"login": "foo"},
                },
            }
        ),
    ),
)
def test_process_message(event):
    packit_yaml = (
        "{'specfile_path': '', 'synced_files': []"
        ", jobs: [{trigger: release, job: propose_downstream}]}"
    )
    flexmock(Github, get_repo=lambda full_name_or_id: None)
    flexmock(
        GithubProject,
        get_file_content=lambda path, ref: packit_yaml,
        full_repo_name="foo/bar",
    )
    flexmock(LocalProject, refresh_the_arguments=lambda: None)
    flexmock(PackitAPI, sync_release=lambda dist_git_branch, version: None)
    c = Config()
    s = SteveJobs(c)
    s.process_message(event)
