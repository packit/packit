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
import datetime
from flexmock import flexmock
from rebasehelper.specfile import SpecFile

from packit.config import get_local_package_config
from packit.status import Status
from tests.spellbook import get_test_config, can_a_module_be_imported
from tests.integration.bodhi_status_updates import BODHI_UPDATES
from tests.integration.bodhi_latest_builds import BODHI_LATEST_BUILDS
from packit.distgit import DistGit
from ogr.services.pagure import PagureProject, PagureService
from ogr.abstract import PullRequest, PRStatus, Release


@pytest.mark.parametrize(
    "pr_list,number_prs",
    [
        (
            [
                PullRequest(
                    id=1,
                    title="PR1",
                    url="URL1",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=2,
                    title="PR2",
                    url="URL2",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=3,
                    title="PR3",
                    url="URL3",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=4,
                    title="PR4",
                    url="URL4",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
            ],
            4,
        ),
        (
            [
                PullRequest(
                    id=1,
                    title="PR1",
                    url="URL1",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=2,
                    title="PR2",
                    url="URL2",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=3,
                    title="PR3",
                    url="URL3",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=4,
                    title="PR4",
                    url="URL4",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
            ],
            1,
        ),
        (
            [
                PullRequest(
                    id=1,
                    title="PR1",
                    url="URL1",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                )
            ],
            1,
        ),
        (
            [
                PullRequest(
                    id=1,
                    title="PR1",
                    url="URL1",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=2,
                    title="PR2",
                    url="URL2",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=3,
                    title="PR3",
                    url="URL3",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
                PullRequest(
                    id=4,
                    title="PR4",
                    url="URL4",
                    status=PRStatus.all,
                    description="",
                    author="",
                    source_branch="",
                    target_branch="",
                    created=datetime.datetime.fromtimestamp(int(0)),
                ),
            ],
            2,
        ),
    ],
)
def test_downstream_pr(upstream_n_distgit, pr_list, number_prs):
    u, d = upstream_n_distgit

    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)
    pc = get_local_package_config(str(u))
    status = Status(c, pc, u, dg)
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": "foo.git"},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject("", "", PagureService()),
        get_pr_list=pr_list,
    )
    assert status
    table = status.get_downstream_prs(number_prs)
    assert table
    assert len(table) == number_prs


@pytest.mark.skipif(
    not can_a_module_be_imported("bodhi"), reason="bodhi not present, skipping"
)
@pytest.mark.parametrize(
    "expected_status,number_of_updates",
    (
        ([["colin-0.3.1-1.fc29", 1, "stable"], ["colin-0.3.1-1.fc28", 1, "stable"]], 2),
        ([["colin-0.3.1-1.fc29", 1, "stable"]], 1),
        (
            [
                ["colin-0.3.1-1.fc29", 1, "stable"],
                ["colin-0.3.1-1.fc28", 1, "stable"],
                ["colin-0.3.0-2.fc28", 0, "obsolete"],
            ],
            3,
        ),
    ),
)
def test_get_updates(upstream_n_distgit, expected_status, number_of_updates):
    u, d = upstream_n_distgit
    from bodhi.client.bindings import BodhiClient

    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)
    pc = get_local_package_config(str(u))
    flexmock(BodhiClient).should_receive("query").and_return(BODHI_UPDATES)
    status = Status(c, pc, u, dg)
    assert status
    table = status.get_updates(number_of_updates=number_of_updates)
    assert table
    assert len(table) == number_of_updates
    assert table == expected_status


@pytest.mark.skipif(
    not can_a_module_be_imported("bodhi"), reason="bodhi not present, skipping"
)
@pytest.mark.parametrize(
    "expected_results,br_list",
    (
        ({"f30": "colin-0.3.1-2.fc30"}, ["f30", "master"]),
        ({"f27": "colin-0.2.0-1.fc27"}, ["f27", "master"]),
        ({"f28": "colin-0.3.1-1.fc28"}, ["f28", "master"]),
        (
            {
                "f27": "colin-0.2.0-1.fc27",
                "f28": "colin-0.3.1-1.fc28",
                "f29": "colin-0.3.1-1.fc29",
                "f30": "colin-0.3.1-2.fc30",
            },
            ["f27", "f28", "f29", "f30", "master"],
        ),
        ({"f30": "colin-0.3.1-2.fc30"}, ["f30", "master"]),
    ),
)
def test_get_builds(upstream_n_distgit, expected_results, br_list):
    u, d = upstream_n_distgit
    from bodhi.client.bindings import BodhiClient

    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)
    flexmock(BodhiClient).should_receive("latest_builds").and_return(
        BODHI_LATEST_BUILDS
    )
    status = Status(c, pc, u, dg)
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": "foo.git"},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject("", "", PagureService()),
        get_branches=br_list,
    )
    assert status
    table = status.get_builds()
    assert table
    assert table == expected_results


@pytest.mark.parametrize(
    "expected_releases",
    (
        (
            [
                Release(
                    "Release title1",
                    "beer1",
                    "0.0.1",
                    "www.packit.dev",
                    "23-5-2018",
                    "www.packit.dev/tarball1",
                ),
                Release(
                    "Release title2",
                    "beer2",
                    "0.0.2",
                    "www.packit.dev",
                    "23-6-2018",
                    "www.packit.dev/tarball2",
                ),
                Release(
                    "Release title3",
                    "beer3",
                    "0.0.3",
                    "www.packit.dev",
                    "23-7-2018",
                    "www.packit.dev/tarball3",
                ),
            ]
        ),
        (
            [
                Release(
                    "Release title1",
                    "beer1",
                    "0.0.1",
                    "www.packit.dev",
                    "23-5-2018",
                    "www.packit.dev/tarball1",
                )
            ]
        ),
    ),
)
def test_get_releases(upstream_instance, distgit_instance, expected_releases):
    u, up = upstream_instance
    d, dg = distgit_instance
    c = get_test_config()
    pc = get_local_package_config(str(u))
    up.local_project.git_project = flexmock()

    flexmock(up.local_project.git_project).should_receive("get_releases").and_return(
        expected_releases
    )
    status = Status(c, pc, up, dg)
    releases = status.get_up_releases()
    assert len(releases) == len(expected_releases)
    assert releases == expected_releases


@pytest.mark.parametrize(
    "expected_versions", ({"master": "0.0.2", "f29": "0.0.2", "f28": "0.0.2"},)
)
def test_get_dg_versions(upstream_n_distgit, expected_versions):
    u, d = upstream_n_distgit

    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)

    flexmock(dg.local_project.git_project).should_receive("get_branches").and_return(
        expected_versions.keys()
    )
    flexmock(SpecFile).should_receive("get_version").and_return("0.0.2")
    flexmock(dg).should_receive("checkout_branch").and_return(None)
    flexmock(dg).should_receive("create_branch").and_return(None)

    status = Status(c, pc, u, dg)
    dg_versions = status.get_dg_versions()
    assert dg_versions.keys() == expected_versions.keys()
    assert dg_versions == expected_versions
