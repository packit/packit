# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.exceptions import PackitException
from packit.patches import PatchMetadata
from packit.constants import DISTRO_DIR


def test_update_source_git_sources_changed(
    sourcegit_and_remote,
    distgit_and_remote,
    api_instance_update_source_git,
):
    """Checks that an error is thrown when sources in dist-git were modified."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    (distgit / "sources").write_text("abcd")
    api_instance_update_source_git.dg.commit("Update sources", "")
    with pytest.raises(PackitException):
        api_instance_update_source_git.update_source_git("HEAD~1..")


def test_update_source_git_patch_changed(
    sourcegit_and_remote,
    distgit_and_remote,
    api_instance_update_source_git,
):
    """Checks that an error is thrown when a patch was modified in the
    given commit."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    patch = "something.patch"
    (distgit / patch).write_text("abcd")
    api_instance_update_source_git.dg.specfile.add_patch(PatchMetadata(name=patch))
    api_instance_update_source_git.dg.specfile.save()
    api_instance_update_source_git.dg.commit("Add a patch", "")
    with pytest.raises(PackitException):
        api_instance_update_source_git.update_source_git("HEAD~1..")


def test_update_source_git_gitignore_empty_commit(
    sourcegit_and_remote,
    distgit_and_remote,
    api_instance_update_source_git,
):
    """Checks that inapplicable gitignore changes do not cause an error
    when a commit contains only the gitignore change."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    (sourcegit / DISTRO_DIR / ".gitignore").write_text("# Reset gitignore\n!*\n")
    (distgit / ".gitignore").write_text("# Former gitignore\na\nb\n")
    api_instance_update_source_git.dg.commit("Setup gitignore", "")
    api_instance_update_source_git.up.commit("Reset gitignore", "")
    # Should not raise on gitignore changes
    api_instance_update_source_git.update_source_git("HEAD~1..")
    # There is nothing to commit in the gitignore patch, head should stay the same
    assert (
        "Reset"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )


def test_update_source_git_gitignore(
    sourcegit_and_remote,
    distgit_and_remote,
    api_instance_update_source_git,
):
    """Checks that inapplicable gitignore changes do not cause an error but
    the rest of the commit is applied."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    (sourcegit / DISTRO_DIR / ".gitignore").write_text("# Reset gitignore\n!*\n")
    (distgit / ".gitignore").write_text("# Former gitignore\na\nb\n")
    content = "abcd"
    (distgit / "c").write_text(content)
    api_instance_update_source_git.dg.commit("Setup gitignore", "")
    api_instance_update_source_git.up.commit("Reset gitignore", "")
    # Should not raise on gitignore changes
    api_instance_update_source_git.update_source_git("HEAD~1..")
    assert content == (sourcegit / DISTRO_DIR / "c").read_text()
    assert (
        "Setup"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )


def test_update_source_git(
    sourcegit_and_remote,
    distgit_and_remote,
    api_instance_update_source_git,
):
    """Updates source-git based on multiple 'extra' commits in the dist-git,
    tests the various possible types of changes of the commit:

    - file creation
    - file modification
    - file rename
    - file removal
    """
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    # Create a new file
    new_file = "test_file.txt"
    content = "abcd"
    (distgit / new_file).write_text(content)
    api_instance_update_source_git.dg.commit("Add", "")
    api_instance_update_source_git.update_source_git("HEAD~1..")
    assert (sourcegit / DISTRO_DIR / new_file).read_text() == content
    assert (
        "Add"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )
    assert (
        f"From-dist-git-commit: "
        f"{api_instance_update_source_git.dg.local_project.git_repo.head.commit.hexsha}"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )

    # Modify the existing file
    extra_content = "\ndefgh"
    with open(distgit / new_file, "a") as file:
        file.write(extra_content)
    api_instance_update_source_git.dg.commit("Modify", "")
    api_instance_update_source_git.update_source_git("HEAD~1..")
    assert (sourcegit / DISTRO_DIR / new_file).read_text() == content + extra_content
    assert (
        "Modify"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )
    assert (
        f"From-dist-git-commit: "
        f"{api_instance_update_source_git.dg.local_project.git_repo.head.commit.hexsha}"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )

    # Rename a file
    new_name = "test.txt"
    (distgit / new_file).rename(distgit / new_name)
    api_instance_update_source_git.dg.commit("Rename", "")
    api_instance_update_source_git.update_source_git("HEAD~1..")
    assert not (sourcegit / DISTRO_DIR / new_file).exists()
    with open(sourcegit / DISTRO_DIR / new_name, "r") as file:
        assert file.read() == content + extra_content
    assert (
        "Rename"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )
    assert (
        f"From-dist-git-commit: "
        f"{api_instance_update_source_git.dg.local_project.git_repo.head.commit.hexsha}"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )

    # Delete a file
    (distgit / new_name).unlink()
    api_instance_update_source_git.dg.commit("Delete", "")
    api_instance_update_source_git.update_source_git("HEAD~1..")
    assert not (sourcegit / DISTRO_DIR / new_name).exists()
    assert (
        "Delete"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )
    assert (
        f"From-dist-git-commit: "
        f"{api_instance_update_source_git.dg.local_project.git_repo.head.commit.hexsha}"
        in api_instance_update_source_git.up.local_project.git_repo.head.commit.message
    )
