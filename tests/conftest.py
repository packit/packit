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

import datetime
import os
import shutil
import subprocess
from os import chdir
from pathlib import Path

import pytest
from flexmock import flexmock
from ogr.abstract import PullRequest, PRStatus
from ogr.services.github import GithubService, GithubProject
from ogr.services.our_pagure import OurPagure
from ogr.services.pagure import PagureProject, PagureService
from rebasehelper.specfile import SpecFile

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.distgit import DistGit
from packit.fedpkg import FedPKG
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import (
    prepare_dist_git_repo,
    get_test_config,
    SOURCEGIT_UPSTREAM,
    SOURCEGIT_SOURCEGIT,
    git_add_and_commit,
    TARBALL_NAME,
    UPSTREAM,
    initiate_git_repo,
    DISTGIT,
)
from tests.utils import cwd

DOWNSTREAM_PROJECT_URL = "https://src.fedoraproject.org/not/set.git"
UPSTREAM_PROJECT_URL = "https://github.com/also-not/set.git"


@pytest.fixture()
def mock_downstream_remote_functionality(downstream_n_distgit):
    u, d = downstream_n_distgit

    flexmock(DistGit, update_branch=lambda *args, **kwargs: "0.0.0")

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = d / TARBALL_NAME
        hops_filename = "hops"
        hops_path = d / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(["tar", "-cf", str(tarball_path), hops_filename], cwd=d)

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)

    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    return u, d


@pytest.fixture()
def mock_remote_functionality_upstream(upstream_n_distgit):
    u, d = upstream_n_distgit
    return mock_remote_functionality(d, u)


@pytest.fixture()
def mock_remote_functionality_sourcegit(sourcegit_n_distgit):
    u, d = sourcegit_n_distgit
    return mock_remote_functionality(d, u)


def mock_remote_functionality(distgit, upstream):
    def mocked_pr_create(*args, **kwargs):
        return PullRequest(
            title="",
            id=42,
            status=PRStatus.open,
            url="",
            description="",
            author="",
            source_branch="",
            target_branch="",
            created=datetime.datetime(1969, 11, 11, 11, 11, 11, 11),
        )

    flexmock(GithubService)
    github_service = GithubService()
    flexmock(
        GithubService,
        get_project=lambda repo, namespace: GithubProject(
            "also-not", github_service, "set", github_repo=flexmock()
        ),
    )
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": DOWNSTREAM_PROJECT_URL},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject("", "", PagureService()),
        pr_create=mocked_pr_create,
    )
    flexmock(
        OurPagure,
        get_git_urls=lambda: {"git": DOWNSTREAM_PROJECT_URL},
        get_fork=lambda: PagureProject("", "", flexmock()),
    )
    flexmock(
        GithubProject,
        get_git_urls=lambda: {"git": UPSTREAM_PROJECT_URL},
        fork_create=lambda: None,
    )

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = distgit / TARBALL_NAME
        hops_filename = "hops"
        hops_path = distgit / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(
            ["tar", "-cf", str(tarball_path), hops_filename], cwd=distgit
        )

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)
    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        # let's not hammer the production lookaside cache webserver
        is_archive_in_lookaside_cache=lambda archive_path: False,
        build=lambda scratch: None,
    )

    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")

    flexmock(FedPKG, init_ticket=lambda x=None: None, new_sources=mocked_new_sources)
    pc = get_local_package_config(str(upstream))
    pc.downstream_project_url = str(distgit)
    pc.upstream_project_url = str(upstream)
    return upstream, distgit


@pytest.fixture()
def mock_patching():
    flexmock(Upstream).should_receive("create_patches").and_return(["patches"])
    flexmock(DistGit).should_receive("add_patches_to_specfile").with_args(["patches"])


@pytest.fixture()
def upstream_n_distgit(tmpdir):
    t = Path(str(tmpdir))

    u_remote = t / "upstream_remote"
    u_remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=u_remote)

    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    initiate_git_repo(u, tag="0.1.0")

    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    initiate_git_repo(d, push=True, upstream_remote=str(u_remote))
    prepare_dist_git_repo(d)

    return u, d


@pytest.fixture()
def sourcegit_n_distgit(tmpdir):
    temp_dir = Path(str(tmpdir))

    sourcegit_remote = temp_dir / "source_git_remote"
    sourcegit_remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=sourcegit_remote)

    sourcegit_dir = temp_dir / "source_git"
    shutil.copytree(SOURCEGIT_UPSTREAM, sourcegit_dir)
    initiate_git_repo(sourcegit_dir, tag="0.1.0")
    subprocess.check_call(
        ["cp", "-R", SOURCEGIT_SOURCEGIT, temp_dir], cwd=sourcegit_remote
    )
    git_add_and_commit(directory=sourcegit_dir, message="sourcegit content")

    distgit_dir = temp_dir / "dist_git"
    shutil.copytree(DISTGIT, distgit_dir)
    initiate_git_repo(distgit_dir, push=True, upstream_remote=str(sourcegit_remote))
    prepare_dist_git_repo(distgit_dir)

    return sourcegit_dir, distgit_dir


@pytest.fixture()
def downstream_n_distgit(tmpdir):
    t = Path(str(tmpdir))

    d_remote = t / "downstream_remote"
    d_remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=d_remote)

    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    initiate_git_repo(d, tag="0.0.0")

    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    initiate_git_repo(u, push=False, upstream_remote=str(d_remote))

    return u, d


@pytest.fixture()
def upstream_instance(upstream_n_distgit, tmpdir):

    with cwd(tmpdir):
        u, d = upstream_n_distgit
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        pc.downstream_project_url = str(d)
        lp = LocalProject(path_or_url=str(u))

        ups = Upstream(c, pc, lp)
        yield u, ups


@pytest.fixture()
def upstream_instance_with_two_commits(upstream_instance):
    u, ups = upstream_instance
    new_file = u / "new.file"
    new_file.write_text("Some content")
    git_add_and_commit(u, message="Add new file")
    return u, ups


@pytest.fixture()
def distgit_instance(upstream_n_distgit, mock_remote_functionality_upstream):
    u, d = upstream_n_distgit
    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)
    return d, dg


@pytest.fixture()
def api_instance(upstream_n_distgit):
    u, d = upstream_n_distgit

    # we need to chdir(u) because when PackageConfig is created,
    # it already expects it's in the correct directory
    old_cwd = os.getcwd()
    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    up_lp = LocalProject(path_or_url=str(u))

    api = PackitAPI(c, pc, up_lp)
    yield u, d, api
    chdir(old_cwd)


@pytest.fixture()
def api_instance_source_git(sourcegit_n_distgit):
    sourcegit, distgit = sourcegit_n_distgit
    with cwd(sourcegit):
        c = get_test_config()
        pc = get_local_package_config(str(sourcegit))
        pc.upstream_project_url = str(sourcegit)
        pc.downstream_project_url = str(distgit)
        up_lp = LocalProject(path_or_url=str(sourcegit))
        api = PackitAPI(c, pc, up_lp)
        return api
