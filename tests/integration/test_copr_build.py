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
from copr.v3 import ProjectProxy, Client, BuildProxy, CoprNoResultException

from flexmock import flexmock
from packit.copr_helper import CoprHelper
from packit.exceptions import PackitCoprException


def test_copr_build_existing_project(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"

    flexmock(ProjectProxy).should_receive("get").and_return(
        flexmock(chroot_repos=flexmock(keys=lambda: {"fedora-rawhide-x86_64"}))
    )
    flexmock(ProjectProxy).should_receive("edit").and_return(None)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"})
    )

    build = flexmock(id="1", ownername=owner, projectname=project)
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots="fedora-rawhide-x86_64",
        owner=owner,
        description="some description",
        instructions="the instructions",
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_non_existing_project(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"

    flexmock(ProjectProxy).should_receive("get").and_raise(
        CoprNoResultException, "project not found"
    )
    flexmock(ProjectProxy).should_receive("edit").and_return(None).times(0)
    flexmock(ProjectProxy).should_receive("add").and_return(None)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(
            config={"copr_url": "https://copr.fedorainfracloud.org", "username": owner}
        )
    )

    build = flexmock(id="1", ownername=owner, projectname=project)
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots="fedora-rawhide-x86_64",
        owner=owner,
        description="some description",
        instructions="the instructions",
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_no_owner(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"})
    )
    with pytest.raises(PackitCoprException) as ex:
        api.run_copr_build(
            project="project-name",
            chroots="fedora-rawhide-x86_64",
            owner=None,
            description="some description",
            instructions="the instructions",
        )
    assert "owner not set" in str(ex)
