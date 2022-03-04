# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.exceptions import PackitException
from packit.api import PackitAPI, SynchronizationStatus
from tests.integration.conftest import mock_spec_download_remote_s
from packit.constants import DISTRO_DIR, FROM_SOURCE_GIT_TOKEN, FROM_DIST_GIT_TOKEN


@pytest.fixture
def check_ready_api_dg_first(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_update_source_git,
) -> PackitAPI:
    """Fixture returning an API instance where dist-git and source-git
    repos contain commits with git-trailers. The latest trailing commit
    is source-git update (From-dist-git trailer)."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)
    api_instance_update_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
        mark_commit_origin=True,
    )
    (distgit / "file").write_text("foo")
    api_instance_update_source_git.dg.commit("add new file", "")
    api_instance_update_source_git.update_source_git("HEAD~..")
    return api_instance_update_source_git


@pytest.fixture
def check_ready_api_sg_first(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_update_source_git,
) -> PackitAPI:
    """Fixture returning an API instance where dist-git and source-git
    repos contain commits with git-trailers. The latest trailing commit
    is dist-git update (From-source-git trailer)."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    (distgit / "file").write_text("foo")
    api_instance_update_source_git.dg.commit("add new file", "")
    api_instance_update_source_git.update_source_git("HEAD~..")
    mock_spec_download_remote_s(distgit)
    api_instance_update_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
        mark_commit_origin=True,
    )
    return api_instance_update_source_git


def test_source_git_status_no_trailers(
    sourcegit_and_remote, distgit_and_remote, api_instance_source_git
):
    """Check that an error is thrown if no trailers are present."""
    with pytest.raises(PackitException):
        api_instance_source_git.sync_status()


def test_source_git_status_dg_commit_not_exists(
    sourcegit_and_remote, distgit_and_remote, api_instance_source_git
):
    """Check that an error is thrown if dist-git commit referenced
    by a From-dist-git trailer does not exist."""
    sourcegit, _ = sourcegit_and_remote
    (sourcegit / "file").write_text("foo")
    api_instance_source_git.up.commit(
        "change", "", trailers=[(FROM_SOURCE_GIT_TOKEN, "abcd")]
    )
    with pytest.raises(PackitException):
        api_instance_source_git.sync_status()


def test_source_git_status_sg_commit_not_exists(
    sourcegit_and_remote, distgit_and_remote, api_instance_source_git
):
    """Check that an error is thrown if source-git commit referenced
    by a From-source-git trailer does not exist."""
    distgit, _ = distgit_and_remote
    (distgit / "file").write_text("foo")
    api_instance_source_git.dg.commit(
        "change", "", trailers=[(FROM_DIST_GIT_TOKEN, "abcd")]
    )
    with pytest.raises(PackitException):
        api_instance_source_git.sync_status()


@pytest.mark.parametrize(
    "api", ["check_ready_api_dg_first", "check_ready_api_sg_first"]
)
def test_source_git_status_synced(
    sourcegit_and_remote, distgit_and_remote, api, request
):
    """Dist-git and source-git are in sync."""
    api_instance = request.getfixturevalue(api)
    assert api_instance.sync_status() == SynchronizationStatus(None, None)


@pytest.mark.parametrize(
    "api", ["check_ready_api_dg_first", "check_ready_api_sg_first"]
)
def test_source_git_status_dist_git_ahead(
    sourcegit_and_remote, distgit_and_remote, api, request
):
    """Dist-git has extra commits that must be synced."""
    api_instance = request.getfixturevalue(api)
    distgit, _ = distgit_and_remote
    (distgit / "file").write_text("aaa")
    api_instance.dg.commit("changes", "")
    range_start = api_instance.dg.local_project.git_repo.head.commit.hexsha
    (distgit / "file").write_text("aaaa")
    api_instance.dg.commit("changes", "")
    assert api_instance.sync_status() == SynchronizationStatus(None, range_start)


@pytest.mark.parametrize(
    "api", ["check_ready_api_dg_first", "check_ready_api_sg_first"]
)
def test_source_git_status_source_git_ahead(
    sourcegit_and_remote, distgit_and_remote, api, request
):
    """Source-git has extra commits that must be synced."""
    api_instance = request.getfixturevalue(api)
    sourcegit, _ = sourcegit_and_remote
    (sourcegit / DISTRO_DIR / "new_file").write_text("bbbb")
    api_instance.up.commit("changes to source-git", "")
    sg_range_start = api_instance.up.local_project.git_repo.head.commit.hexsha
    assert api_instance.sync_status() == SynchronizationStatus(sg_range_start, None)


@pytest.mark.parametrize(
    "api", ["check_ready_api_dg_first", "check_ready_api_sg_first"]
)
def test_source_git_status_history_diverges(
    sourcegit_and_remote, distgit_and_remote, api, request
):
    """Both source-git and dist-git have extra commits that must be
    synced (diversion)."""
    api_instance = request.getfixturevalue(api)
    distgit, _ = distgit_and_remote
    sourcegit, _ = sourcegit_and_remote
    (distgit / "file").write_text("aaa")
    api_instance.dg.commit("changes", "")
    dg_range_start = api_instance.dg.local_project.git_repo.head.commit.hexsha
    (distgit / "file").write_text("aaaa")
    api_instance.dg.commit("changes", "")

    (sourcegit / DISTRO_DIR / "new_file").write_text("bbbb")
    api_instance.up.commit("changes to source-git", "")
    sg_range_start = api_instance.up.local_project.git_repo.head.commit.hexsha
    assert api_instance.sync_status() == SynchronizationStatus(
        sg_range_start, dg_range_start
    )
