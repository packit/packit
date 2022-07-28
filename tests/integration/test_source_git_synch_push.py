# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from flexmock import flexmock
import pytest

from packit.exceptions import PackitException
from packit.upstream import Upstream


def test_synch_push_and_up_repo_dirty(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_sync_push,
):
    """Check that exception is raised when upstream repo is dirty"""

    sourcegit, _ = sourcegit_and_remote
    (sourcegit / "README").write_text("a change in the repo")

    with pytest.raises(PackitException) as exc:
        api_instance_sync_push.sync_push()

    assert "is dirty" in str(exc.value)


def test_synch_push_and_dg_repo_dirty(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_sync_push,
):
    """Check that exception is raised when dist-git repo is dirty"""
    distgit, _ = distgit_and_remote
    (distgit / "README").write_text("a change in the repo")

    with pytest.raises(PackitException) as exc:
        api_instance_sync_push.sync_push()

    assert "is dirty" in str(exc.value)


def test_synch_push_and_diverged_repos(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_sync_push,
):
    """Check that exception is raised when upstream and dist-git repos have diverged"""

    api_instance_sync_push.up.specfile.version = "2.3.4"
    api_instance_sync_push.up.commit("Source-git commit to be synced", "")

    with pytest.raises(PackitException) as exc:
        api_instance_sync_push.sync_push()

    assert "diverged" in str(exc.value)


def test_synch_push_one_commit(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_sync_push,
):
    """Update upstream if dist-git has a new commit"""

    flexmock(Upstream).should_receive("push_to_fork").and_return(
        "main", "packit.dev"
    ).once()
    flexmock(Upstream).should_receive("create_pull").and_return(None).once()

    assert (
        "dist-git commit to be sync back"
        not in api_instance_sync_push.up.local_project.git_repo.head.commit.message
    )

    api_instance_sync_push.sync_push()

    assert (
        "dist-git commit to be sync back"
        in api_instance_sync_push.up.local_project.git_repo.head.commit.message
    )


def test_synch_push_two_commits(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_sync_push,
):
    """Update upstream if dist-git has a new commit"""
    api_instance_sync_push.dg.specfile.version = "3.4.5"
    api_instance_sync_push.dg.commit(
        "Another dist-git commit to be synced back\n\nWith a multiline\ndescription", ""
    )

    flexmock(Upstream).should_receive("push_to_fork").and_return(
        "main", "packit.dev"
    ).once()
    flexmock(Upstream).should_receive("create_pull").and_return(None).once()

    commits = api_instance_sync_push.up.local_project.git_repo.iter_commits()
    commits = [c.summary for c in commits]
    assert "dist-git commit to be sync back" not in commits
    assert "Another dist-git commit to be synced back" not in commits

    api_instance_sync_push.sync_push()

    commits = api_instance_sync_push.up.local_project.git_repo.iter_commits()
    commits = [c.summary for c in commits]
    assert "[packit] dist-git commit to be sync back" in commits
    assert "[packit] Another dist-git commit to be synced back" in commits
