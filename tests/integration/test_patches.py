# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil
import textwrap
from pathlib import Path

import git
import pytest
from flexmock import flexmock

from packit.exceptions import PackitException
from packit.patches import PatchGenerator, PatchMetadata
from tests.spellbook import DATA_DIR

TESTS_DIR = str(Path(__file__).parent.parent)


def check_copytree_dirs_exists_support():
    """
    Old version of shutil.copytree does not support
    dirs_exist_ok parameter.
    """
    return bool(
        hasattr(shutil.copytree, "__defaults__")
        and len(shutil.copytree.__defaults__) >= 5,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> git.Repo:
    """
    Set up a git repo with some initial patch files in the history,
    and the same patch files updated after re-generating them from a
    source-git repo.
    """
    repo_dir = tmp_path.joinpath("repo")
    shutil.copytree(
        src=f"{DATA_DIR}/patches/previous/",
        dst=str(repo_dir),
    )
    repo = git.Repo.init(repo_dir)
    repo.git.add(repo.working_tree_dir)
    repo.git.commit("-mInitial patches")
    shutil.copytree(
        src=f"{DATA_DIR}/patches/regenerated/",
        dst=repo.working_tree_dir,
        dirs_exist_ok=True,
    )
    return repo


@pytest.mark.skipif(
    not check_copytree_dirs_exists_support(),
    reason="Old python version does not support copytree exists dirs parameter"
    " https://github.com/packit/packit/issues/1160",
)
def test_undo_identical(git_repo):
    """
    Check that identical patches are correctly detected and changes
    undone in the target git repo.
    """
    input_patch_list = [
        PatchMetadata(name=path.name, path=path)
        for path in Path(git_repo.working_tree_dir).iterdir()
        if path.suffix == ".patch"
    ]
    output_patch_list = [
        x for x in input_patch_list if x.name == "weird-identical.patch"
    ]
    assert (
        PatchGenerator.undo_identical(input_patch_list, git_repo) == output_patch_list
    )
    # 'weird-identical.patch' is identical, except the original patch file
    # is missing a "function" name at one of the hunks, which causes the
    # patch-ids to be different.
    # Is there any safe way to handle this?
    assert [item.a_path for item in git_repo.index.diff(None)] == [
        "weird-identical.patch",
    ]


@pytest.fixture
def source_git_repo(tmp_path: Path) -> git.Repo:
    repo_dir = tmp_path.joinpath("src/hello")
    shutil.copytree(
        src=f"{DATA_DIR}/patches/src/hello/",
        dst=str(repo_dir),
    )
    repo = git.Repo.init(repo_dir)
    repo.git.add(repo.working_dir)
    repo.git.commit("-mInitial commit")
    repo.git.tag("0.1.0")
    return repo


@pytest.fixture
def dist_git_repo(tmp_path: Path) -> git.Repo:
    repo_dir = tmp_path.joinpath("rpms/hello")
    shutil.copytree(
        src=f"{DATA_DIR}/patches/rpms/hello/",
        dst=str(repo_dir),
    )
    repo = git.Repo.init(repo_dir)
    repo.git.add(repo.working_dir)
    repo.git.commit("-mInitial commit")
    return repo


def create_commits_to_squash(repo: git.Repo):
    readme = Path(repo.working_dir, "README.md")

    readme.write_text(f"{readme.read_text()}\nThe first standalone patch.\n")
    repo.git.add("README.md")
    repo.git.commit("-mAdd a standalone patch")

    readme.write_text(f"{readme.read_text()}\nThe first commit of the second patch.\n")
    repo.git.add("README.md")
    commit_message = textwrap.dedent(
        """\
        Add a distro change

        patch_name: distro.patch
        """,
    )
    repo.git.commit(f"-m{commit_message}")

    readme.write_text(f"{readme.read_text()}\nThe second commit of the second patch.\n")
    repo.git.add("README.md")
    commit_message = textwrap.dedent(
        """\
        Another distro change

        patch_name: distro.patch
        """,
    )
    repo.git.commit(f"-m{commit_message}")

    readme.write_text(f"{readme.read_text()}\nThe second standalone patch.\n")
    repo.git.add("README.md")
    repo.git.commit("-mAdd another standalone patch")


def test_squash_patches_by_name(source_git_repo: git.Repo, dist_git_repo: git.Repo):
    """Patch files corresponding to commits which have identical 'patch_name'
    metadata defined are squashed.
    """
    local_project = flexmock(
        git_repo=source_git_repo,
        ref="HEAD",
        working_dir=source_git_repo.working_dir,
    )

    create_commits_to_squash(source_git_repo)

    patch_generator = PatchGenerator(local_project)
    patch_list = patch_generator.create_patches(
        git_ref="0.1.0",
        destination=dist_git_repo.working_dir,
    )
    assert len(patch_list) == 3
    assert patch_list[1].path == Path(dist_git_repo.working_dir, "distro.patch")
    assert patch_list[1].name == "distro.patch"
    assert sorted(dist_git_repo.untracked_files) == [
        "0001-Add-a-standalone-patch.patch",
        "0004-Add-another-standalone-patch.patch",
        "distro.patch",
    ]
    patch = Path(dist_git_repo.working_dir, "distro.patch").read_text()
    assert "+The first commit of the second patch." in patch
    assert "+The second commit of the second patch." in patch


def create_non_adjacent_commits_to_squash(repo: git.Repo):
    """Patch files corresponding to non-adjacent commits, which should be squashed
    by name are not squashed and an exception is raised."""
    readme = Path(repo.working_dir, "README.md")

    readme.write_text(f"{readme.read_text()}\nThe first change.\n")
    repo.git.add("README.md")
    commit_message = textwrap.dedent(
        """\
        First commit

        patch_name: non_adjacent.patch
        """,
    )
    repo.git.commit(f"-m{commit_message}")

    readme = Path(repo.working_dir, "README.md")
    readme.write_text(f"{readme.read_text()}\nThe second change.\n")
    repo.git.add("README.md")
    commit_message = "Second commit"
    repo.git.commit(f"-m{commit_message}")

    readme = Path(repo.working_dir, "README.md")
    readme.write_text(f"{readme.read_text()}\nThe third change.\n")
    repo.git.add("README.md")
    commit_message = textwrap.dedent(
        """\
        Third commit

        patch_name: non_adjacent.patch
        """,
    )
    repo.git.commit(f"-m{commit_message}")


def test_fail_if_not_adjacent(source_git_repo: git.Repo, dist_git_repo: git.Repo):
    local_project = flexmock(
        git_repo=source_git_repo,
        ref="HEAD",
        working_dir=source_git_repo.working_dir,
    )

    create_non_adjacent_commits_to_squash(source_git_repo)

    patch_generator = PatchGenerator(local_project)
    with pytest.raises(PackitException) as ex:
        patch_generator.create_patches(
            git_ref="0.1.0",
            destination=dist_git_repo.working_dir,
        )
    assert "Non-adjacent patches" in str(ex)
