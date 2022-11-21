# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
E2E tests which utilize cockpit projects
"""
import shutil
from pathlib import Path

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.distgit import DistGit
from packit.pkgtool import PkgTool
from packit.local_project import LocalProject
from packit.utils import repo
from packit.utils.commands import cwd
from tests.spellbook import UP_COCKPIT_OSTREE, initiate_git_repo, get_test_config


@pytest.fixture()
def cockpit_ostree(tmp_path, upstream_without_config):
    u = tmp_path / "up"
    initiate_git_repo(u, tag="179", copy_from=UP_COCKPIT_OSTREE)

    flexmock(repo, get_namespace_and_repo_name=lambda url: ("asd", "qwe"))
    d = tmp_path / "dg"
    d.mkdir()
    initiate_git_repo(d, upstream_remote=upstream_without_config, push=True)

    shutil.copy2(
        UP_COCKPIT_OSTREE / "cockpit-ostree.spec.dg", d / "cockpit-ostree.spec"
    )

    return u, d


def test_update_on_cockpit_ostree(cockpit_ostree):
    upstream_path, dist_git_path = cockpit_ostree

    def mocked_new_sources(sources=None):
        sources = sources or []
        if not all(Path(s).is_file() for s in sources):
            raise RuntimeError("archive does not exist")

    flexmock(PkgTool, new_sources=mocked_new_sources)
    flexmock(PackitAPI, init_kerberos_ticket=lambda: None)

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        is_archive_in_lookaside_cache=lambda archive_path: False,
        upload_to_lookaside_cache=lambda archives, pkg_tool: None,
        download_upstream_archives=lambda: ["the-archive"],
    )
    flexmock(DistGit).should_receive("existing_pr").and_return(None)
    flexmock(
        PackitAPI,
        push_and_create_pr=lambda pr_title, pr_description, git_branch, repo: None,
    )

    pc = get_local_package_config(str(upstream_path))
    up_lp = LocalProject(working_dir=upstream_path)
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)
    api._dg = DistGit(c, pc)
    api._dg._local_project = LocalProject(working_dir=dist_git_path)

    with cwd(upstream_path):
        api.sync_release(
            dist_git_branch="main",
            use_local_content=False,
            version="179",
            force_new_sources=False,
            create_pr=True,
        )


def test_update_on_cockpit_ostree_pr_exists(cockpit_ostree):
    upstream_path, dist_git_path = cockpit_ostree

    def mocked_new_sources(sources=None):
        sources = sources or []
        if not all(Path(s).is_file() for s in sources):
            raise RuntimeError("archive does not exist")

    flexmock(PkgTool, new_sources=mocked_new_sources)
    flexmock(PackitAPI, init_kerberos_ticket=lambda: None)

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        is_archive_in_lookaside_cache=lambda archive_path: False,
        upload_to_lookaside_cache=lambda archives, pkg_tool: None,
        download_upstream_archives=lambda: ["the-archive"],
    )
    pr = flexmock(url="https://example.com/pull/1")
    flexmock(DistGit).should_receive("existing_pr").and_return(pr)

    pc = get_local_package_config(str(upstream_path))
    up_lp = LocalProject(working_dir=upstream_path)
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)
    api._dg = DistGit(c, pc)
    api._dg._local_project = LocalProject(working_dir=dist_git_path)

    with cwd(upstream_path):
        assert pr == api.sync_release(
            dist_git_branch="main",
            use_local_content=False,
            version="179",
            force_new_sources=False,
            create_pr=True,
        )


def test_srpm_on_cockpit_ostree(cockpit_ostree):
    upstream_path, dist_git_path = cockpit_ostree

    pc = get_local_package_config(str(upstream_path))
    up_lp = LocalProject(working_dir=upstream_path)
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)

    with cwd(upstream_path):
        api.create_srpm()
