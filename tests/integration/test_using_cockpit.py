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
E2E tests which utilize cockpit projects
"""
import shutil
from pathlib import Path

import pytest
from flexmock import flexmock

from packit import utils
from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.distgit import DistGit
from packit.fedpkg import FedPKG
from packit.local_project import LocalProject
from packit.utils import cwd
from tests.spellbook import UP_COCKPIT_OSTREE, initiate_git_repo, get_test_config


@pytest.fixture()
def cockpit_ostree(tmpdir, upstream_without_config):
    t = Path(str(tmpdir))

    u = t / "up"
    initiate_git_repo(u, tag="179", copy_from=UP_COCKPIT_OSTREE)

    flexmock(utils, get_namespace_and_repo_name=lambda url: ("asd", "qwe"))
    d = t / "dg"
    d.mkdir()
    initiate_git_repo(d, upstream_remote=upstream_without_config, push=True)

    shutil.copy2(
        UP_COCKPIT_OSTREE / "cockpit-ostree.spec.dg", d / "cockpit-ostree.spec"
    )

    return u, d


def test_update_on_cockpit_ostree(cockpit_ostree):
    upstream_path, dist_git_path = cockpit_ostree

    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")

    flexmock(FedPKG, new_sources=mocked_new_sources)
    flexmock(PackitAPI, init_kerberos_ticket=lambda: None)

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        is_archive_in_lookaside_cache=lambda archive_path: False,
        upload_to_lookaside_cache=lambda path: None,
        download_upstream_archive=lambda: "the-archive",
    )
    flexmock(
        PackitAPI,
        push_and_create_pr=lambda pr_title, pr_description, dist_git_branch: None,
    )

    pc = get_local_package_config(str(upstream_path))
    up_lp = LocalProject(working_dir=str(upstream_path))
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)
    api._dg = DistGit(c, pc)
    api._dg._local_project = LocalProject(working_dir=dist_git_path)

    with cwd(upstream_path):
        api.sync_release(
            "master",
            use_local_content=False,
            version="179",
            force_new_sources=False,
            create_pr=True,
        )


def test_srpm_on_cockpit_ostree(cockpit_ostree):
    upstream_path, dist_git_path = cockpit_ostree

    pc = get_local_package_config(str(upstream_path))
    up_lp = LocalProject(working_dir=str(upstream_path))
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)

    with cwd(upstream_path):
        api.create_srpm()
