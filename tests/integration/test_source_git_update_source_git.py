# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.exceptions import PackitException
from packit.patches import PatchMetadata
from packit.constants import DISTRO_DIR


@pytest.fixture
def update_api(api_instance_source_git):
    # The version in dg is different from up, sync it
    version = api_instance_source_git.up.specfile.get_version()
    api_instance_source_git.dg.specfile.set_version(version)
    api_instance_source_git.dg.specfile.save()
    api_instance_source_git.dg.commit("Update spec", "")
    return api_instance_source_git


def test_update_source_git_sources_changed(
    sourcegit_and_remote,
    distgit_and_remote,
    update_api,
):
    """Checks that an error is thrown when sources in dist-git were modified."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    (distgit / "sources").write_text("abcd")
    update_api.dg.commit("Update sources", "")
    with pytest.raises(PackitException):
        update_api.update_source_git("HEAD~1..")


def test_update_source_git_patch_changed(
    sourcegit_and_remote,
    distgit_and_remote,
    update_api,
):
    """Checks that an error is thrown when a patch was modified in the
    given commit."""
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    patch = "something.patch"
    (distgit / patch).write_text("abcd")
    update_api.dg.specfile.add_patch(PatchMetadata(name=patch))
    update_api.dg.specfile.save()
    update_api.dg.commit("Add a patch", "")
    with pytest.raises(PackitException):
        update_api.update_source_git("HEAD~1..")


def test_update_source_git(
    sourcegit_and_remote,
    distgit_and_remote,
    update_api,
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
    update_api.dg.commit("Add", "")
    update_api.update_source_git("HEAD~1..")
    assert (sourcegit / DISTRO_DIR / new_file).read_text() == content
    assert "Add" in update_api.up.local_project.git_repo.head.commit.message

    # Modify the existing file
    extra_content = "\ndefgh"
    with open(distgit / new_file, "a") as file:
        file.write(extra_content)
    update_api.dg.commit("Modify", "")
    update_api.update_source_git("HEAD~1..")
    assert (sourcegit / DISTRO_DIR / new_file).read_text() == content + extra_content
    assert "Modify" in update_api.up.local_project.git_repo.head.commit.message

    # Rename a file
    new_name = "test.txt"
    (distgit / new_file).rename(distgit / new_name)
    update_api.dg.commit("Rename", "")
    update_api.update_source_git("HEAD~1..")
    assert not (sourcegit / DISTRO_DIR / new_file).exists()
    with open(sourcegit / DISTRO_DIR / new_name, "r") as file:
        assert file.read() == content + extra_content
    assert "Rename" in update_api.up.local_project.git_repo.head.commit.message

    # Delete a file
    (distgit / new_name).unlink()
    update_api.dg.commit("Delete", "")
    update_api.update_source_git("HEAD~1..")
    assert not (sourcegit / DISTRO_DIR / new_name).exists()
    assert "Delete" in update_api.up.local_project.git_repo.head.commit.message
