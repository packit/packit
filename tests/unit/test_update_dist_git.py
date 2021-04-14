# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import textwrap
import git
import flexmock
from packit.update_dist_git import update_dist_git


def test_update_dist_git(tmp_path):
    # set up the source-git repo
    source_git_dir = tmp_path / "src-git/package"
    source_git = git.Repo.init(source_git_dir)

    (source_git_dir / "README.md").touch()
    source_git.git.add(".")
    source_git.git.commit("-m", "Initial commit")

    (source_git_dir / "VERSION").write_text("v1.0")
    source_git.git.add(".")
    source_git.git.commit("-m", "Release v1.0\n")
    source_git.git.tag("v1.0")

    distro_dir = source_git_dir / ".distro"
    distro_dir.mkdir()
    test_dir = distro_dir / "tests"
    test_dir.mkdir()
    (test_dir / "test_file").touch()
    (distro_dir / "package.spec").write_text(
        textwrap.dedent(
            """
        Name:       Package
        Version:    1.0
        Release:    1
        Summary:    A package
        License:    Free

        Source0:    https://example.com/downloads/package.tar.gz

        %description
        This is Package and serves as a test package.
    """
        )
    )
    source_git.git.add(".")
    source_git.git.commit("-m", "Add .distro dir")

    package_config = source_git_dir / ".packit.yaml"
    package_config.write_text(
        textwrap.dedent(
            """
    upstream_ref: v1.0
    """
        )
    )
    source_git.git.add(".")
    source_git.git.commit("-m", "Configure upstream ref")

    (source_git_dir / "README.md").write_text("This is a downstream change.\n")
    source_git.git.commit("-am", "Add a downstream change")
    with open(source_git_dir / "README.md", "a") as fp:
        fp.write("Yet another change done in downstream.\n")
    source_git.git.commit("-am", "Add a new downstream change")
    (distro_dir / "untracked_file").touch()

    # set up the dist-git repo
    dist_git_dir = tmp_path / "dist-git/package"
    dist_git = git.Repo.init(dist_git_dir)

    (dist_git_dir / "package.spec").write_text(
        textwrap.dedent(
            """
        Name:       Package
        Version:    0.9
        Release:    1
        Summary:    A package
        License:    Free

        Source0:    https://example.com/downloads/package.tar.gz

        # Add a downstream change
        # Author: Packit Test Suite <test@example.com>
        Patch0001: 0001-Add-a-downstream-change.patch

        %description
        This is Package and serves as a test package.
    """
        )
    )
    test_dir = dist_git_dir / "tests"
    test_dir.mkdir()
    (test_dir / "test_file").touch()
    dist_git.git.add(".")
    dist_git.git.commit("-m", "Initial commit")

    (dist_git_dir / "sources").write_text("some source")
    dist_git.git.add(".")
    dist_git.git.commit("-m", "Add some sources")

    (dist_git_dir / "0001-Add-a-downstream-change.patch").write_text(
        textwrap.dedent(
            """
    From 91cd0c2ca49734f171a5d7c524db74701d731a6e Mon Sep 17 00:00:00 2001
    From: Packit Test Suite <test@example.com>
    Date: Tue, 30 Mar 2021 08:49:24 +0000
    Subject: [PATCH] Add a downstream change

    ---
     README.md | 1 +
     1 file changed, 1 insertion(+)

    diff --git a/README.md b/README.md
    index e69de29..9059ca6 100644
    --- a/README.md
    +++ b/README.md
    @@ -0,0 +1 @@
    +This is a downstream change.
    --
    2.30.2
    """
        )
    )
    patch_to_be_removed = dist_git_dir / "0002-to-be-removed.patch"
    patch_to_be_removed.touch()
    dist_git.git.add(".")
    dist_git.git.commit("-m", "Create some downstream patches")

    update_dist_git(
        source_git_dir,
        dist_git_dir,
        flexmock(package_config_path=None),
        pkg_tool=None,
        message="Update from source-git",
    )

    changed_dist_git_files = dist_git.git.diff("--name-only", "HEAD~1")
    assert not patch_to_be_removed.exists()
    assert "0001-Add-a-downstream-change.patch" not in changed_dist_git_files
    assert "package.spec" in changed_dist_git_files
    assert "sources" not in changed_dist_git_files
    assert "untracked_file" not in changed_dist_git_files
    assert "tests/test_file" not in changed_dist_git_files

    spec = (dist_git_dir / "package.spec").read_text()
    assert "Patch0001:" in spec
    assert "Patch0002:" in spec
