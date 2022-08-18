# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path

import git
import pytest
from specfile import Specfile
from specfile.exceptions import SourceNumberException

from packit.constants import DISTRO_DIR
from packit.exceptions import PackitException
from packit.patches import PatchGenerator
from packit.utils.commands import cwd
from tests.integration.conftest import mock_spec_download_remote_s
from tests.spellbook import (
    TARBALL_NAME,
    git_add_and_commit,
    build_srpm,
    create_merge_commit_in_source_git,
    create_git_am_style_history,
    create_patch_mixed_history,
    create_history_with_empty_commit,
    run_prep_for_srpm,
    create_history_with_patch_ids,
)


def test_update_dist_git_with_sync_status_check(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_update_source_git,
):
    """Check that exception is raised when there's a commit
    in dist-git which has no origin in source-git.
    """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    api_instance_update_source_git.dg.specfile.version = "0.2.0"
    api_instance_update_source_git.dg.commit("Extra dist-git commit", "")

    api_instance_update_source_git.up.specfile.version = "0.3.0"
    api_instance_update_source_git.up.commit("Source-git commit to be synced", "")

    with pytest.raises(PackitException) as exc:
        api_instance_update_source_git.update_dist_git(
            version=None,
            upstream_ref=None,
            add_new_sources=False,
            force_new_sources=False,
            upstream_tag=None,
            commit_title="",
            commit_msg="",
            check_sync_status=True,
        )
    assert " have diverged." in str(exc.value)


def test_update_dist_git_dist_git_not_pristine(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_update_source_git,
):
    """Check that exception is raised when the
    dist-git repo is not pristine.
    """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    (distgit / "new_file").write_text("abcd")

    api_instance_update_source_git.up.specfile.version = "0.3.0"
    api_instance_update_source_git.up.commit("Source-git commit to be synced", "")

    with pytest.raises(PackitException) as exc:
        api_instance_update_source_git.update_dist_git(
            version=None,
            upstream_ref=None,
            add_new_sources=False,
            force_new_sources=False,
            upstream_tag=None,
            commit_title="",
            commit_msg="",
            check_sync_status=True,
        )
    assert "is not pristine" in str(exc.value)


def test_basic_local_update_without_patching(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git
    Check that the upstream commit hash is saved when 'mock_commit_origin' is set.
    """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
        mark_commit_origin=True,
    )

    assert (distgit / TARBALL_NAME).is_file()
    spec = Specfile(distgit / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (
        f"From-source-git-commit: {git.Repo(sourcegit).head.commit.hexsha}"
        in git.Repo(distgit).head.commit.message
    )


@pytest.mark.parametrize("ref", [None, "0.1.0", "0.1*", "0.*"])
def test_basic_local_update_empty_patch(
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
    ref,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git
    Check that by default commit origin is not marked in dist-git.
    """

    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)
    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref=ref,
    )

    assert (distgit / TARBALL_NAME).is_file()
    spec = Specfile(distgit / "beer.spec")
    assert spec.expanded_version == "0.1.0"

    with spec.patches() as patches:
        assert not patches
    assert "From-source-git-commit" not in git.Repo(distgit).head.commit.message


def test_basic_local_update_patch_content(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git
    Check that commit origin is not marked when 'mark_commit_origin' is set to False.
    """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    create_merge_commit_in_source_git(sourcegit)

    source_file = sourcegit / "big-source-file.txt"
    source_file.write_text("new changes")
    git_add_and_commit(directory=sourcegit, message="source change")

    source_file = sourcegit / "ignored_file.txt"
    source_file.write_text(" And I am sad.")
    git_add_and_commit(directory=sourcegit, message="make a file sad")

    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
        mark_commit_origin=False,
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    assert "From-source-git-commit" not in git.Repo(distgit).head.commit.message
    assert (
        """
-Version:        0.0.0
+Version:        0.1.0"""
        in git_diff
    )
    # Make sure the patches are placed after Source0, but outside %if %endif
    patches = """\
Source0:        %{upstream_name}-%{version}.tar.gz
 %endif
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001:      0001-switching-to-amarillo-hops.patch
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002:      0002-actually-let-s-do-citra.patch
+# source change
+# Author: Packit Test Suite <test@example.com>
+Patch0003:      0003-source-change.patch
 BuildArch:      noarch
"""
    assert patches in git_diff

    assert "Patch0004:" not in git_diff

    assert (
        """ - 0.1.0-1
+- Initial brewing
+
 * Sun Feb 24 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.0.0-1
 - No brewing, yet."""
        in git_diff
    )

    patch_1_3 = """
+Subject: [PATCH 1/3] switching to amarillo hops
+
+---
+ hops | 2 +-
+ 1 file changed, 1 insertion(+), 1 deletion(-)
+
+diff --git a/hops b/hops"""
    assert patch_1_3 in git_diff
    assert (
        """\
+--- a/hops
++++ b/hops
+@@ -1 +1 @@
+-Cascade
++Amarillo
+--"""
        in git_diff
    )

    assert (
        """\
+Subject: [PATCH 2/3] actually, let's do citra
+
+---
+ hops | 2 +-
+ 1 file changed, 1 insertion(+), 1 deletion(-)
+
+diff --git a/hops b/hops"""
        in git_diff
    )
    assert (
        (
            """\
+--- a/hops
++++ b/hops
+@@ -1 +1 @@
+-Amarillo
++Citra
+--"""
        )
        in git_diff
    )

    assert (
        """
+--- a/big-source-file.txt
++++ b/big-source-file.txt
+@@ -1,2 +1 @@
+-This is a testing file
+-containing some text.
++new changes"""
        in git_diff
    )

    # diff of the source files (not synced) should not be directly in the git diff
    assert (
        """
+Subject: [PATCH 3/3] source change
+
+---
+ big-source-file.txt | 3 +--
+ 1 file changed, 1 insertion(+), 2 deletions(-)
+
+diff --git a/big-source-file.txt b/big-source-file.txt"""
        in git_diff
    )

    # ignored file should not be in the diff
    assert "--- a/ignored_file.txt\n" not in git_diff


def test_basic_local_update_patch_content_with_metadata(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git"""

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    create_merge_commit_in_source_git(sourcegit)

    source_file = sourcegit / "big-source-file.txt"
    source_file.write_text("new changes")
    git_add_and_commit(
        directory=sourcegit,
        message="source change\n"
        "patch_name: testing.patch\n"
        "description: Few words for info.",
    )

    source_file = sourcegit / "ignored_file.txt"
    source_file.write_text(" And I am sad.")
    git_add_and_commit(directory=sourcegit, message="make a file sad")

    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001:      0001-switching-to-amarillo-hops.patch
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002:      0002-actually-let-s-do-citra.patch
+# Few words for info.
+Patch0003:      testing.patch
"""
    assert patches in git_diff


def test_basic_local_update_patch_content_with_metadata_and_patch_ignored(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git"""

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    create_merge_commit_in_source_git(sourcegit)

    source_file = sourcegit / "big-source-file.txt"
    source_file.write_text("new changes")
    git_add_and_commit(
        directory=sourcegit,
        message="source change\nignore: true",
    )

    source_file = sourcegit / "ignored_file.txt"
    source_file.write_text(" And I am sad.")
    git_add_and_commit(directory=sourcegit, message="make a file sad")

    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001:      0001-switching-to-amarillo-hops.patch
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002:      0002-actually-let-s-do-citra.patch
"""
    assert patches in git_diff


def test_basic_local_update_patch_content_with_downstream_patch(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """propose-downstream for sourcegit test: mock remote API, use local upstream and dist-git"""

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    create_merge_commit_in_source_git(sourcegit)

    source_file = sourcegit / "ignored_file.txt"
    source_file.write_text(" And I am sad.")
    git_add_and_commit(directory=sourcegit, message="make a file sad")

    api_instance_source_git.sync_release(
        dist_git_branch="main",
        version="0.1.0",
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001:      0001-switching-to-amarillo-hops.patch
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002:      0002-actually-let-s-do-citra.patch
"""
    assert patches in git_diff


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm(mock_remote_functionality_sourcegit, api_instance_source_git, ref):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")
    create_merge_commit_in_source_git(sg_path)
    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)
    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)
    branches = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"], cwd=sg_path
    ).split(b"\n")
    for b in branches:
        if b and b.startswith(b"packit-patches-"):
            raise AssertionError(
                "packit-patches- branch was found - the history shouldn't have been linearized"
            )
    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "0001-switching-to-amarillo-hops.patch",
        "0002-actually-let-s-do-citra.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_merge_storm(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")
    create_merge_commit_in_source_git(sg_path, go_nuts=True)

    # linearization creates a new branch, make some arbitrary moves to verify
    # we end up in the former branch after the build
    subprocess.check_call(["git", "checkout", "-B", "test-branch"], cwd=sg_path)
    subprocess.check_call(["git", "checkout", "main"], cwd=sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)
    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)
    branches = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"], cwd=sg_path
    ).split(b"\n")
    for b in branches:
        if b and b.startswith(b"packit-patches-"):
            break
    else:
        raise AssertionError(
            "packit-patches- branch was not found - this should trigger the linearization"
        )
    # make sure we are on the main branch
    assert (
        "main"
        == subprocess.check_output(["git", "branch", "--show-current"], cwd=sg_path)
        .decode()
        .strip()
    )
    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "0001-MERGE-COMMIT.patch",
        "0002-ugly-merge-commit.patch",
    }


def test_srpm_merge_storm_dirty(api_instance_source_git):
    """verify the linearization is halted when a source-git repo si dirty"""
    ref = "0.1.0"
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, ref)
    create_merge_commit_in_source_git(sg_path, go_nuts=True)
    (sg_path / "malt").write_text("Mordor\n")
    with pytest.raises(PackitException) as ex:
        with cwd("/"):  # let's mimic p-s by having different cwd than the project
            api_instance_source_git.create_srpm(upstream_ref=ref)
    assert "The source-git repo is dirty" in str(ex.value)


def test_linearization(api_instance_source_git):
    ref = "0.1.0"
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, ref)
    create_merge_commit_in_source_git(sg_path, go_nuts=True)
    with cwd("/"):  # let's mimic p-s by having different cwd than the project
        pg = PatchGenerator(api_instance_source_git.upstream_local_project)
        pg.create_patches(ref, sg_path / DISTRO_DIR)
    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "0001-sourcegit-content.patch",
        "0002-MERGE-COMMIT.patch",
        "0003-ugly-merge-commit.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_git_am(mock_remote_functionality_sourcegit, api_instance_source_git, ref):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")

    with api_instance_source_git.up.specfile.prep() as prep:
        prep.autosetup.options.S = "git_am"

    create_git_am_style_history(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "citra.patch",
        "0001-m04r-malt.patch",
        "malt.patch",
    }
    run_prep_for_srpm(srpm_path)
    prep_root = sg_path.joinpath("beerware-0.1.0")
    assert prep_root.joinpath("malt").read_text() == "Munich\n"
    assert prep_root.joinpath("hops").read_text() == "Saaz\n"


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_git_no_prefix_patches(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")

    with api_instance_source_git.up.specfile.sections() as sections:
        sections.package[10:10] = (
            "Patch1: amarillo.patch",
            "Patch2: citra.patch",
            "Patch8: malt.patch",
        )
        sections.prep[0:2] = [
            "%setup -n %{upstream_name}-%{version}",
            "%patch1 -p1",
            "%patch2 -p0",
            "%patch8 -p1",
        ]

    create_patch_mixed_history(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "malt.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_empty_patch(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")

    with api_instance_source_git.up.specfile.sections() as sections:
        sections.package[10:10] = (
            "Patch1: amarillo.patch",
            "Patch2: citra.patch",
            "Patch5: saaz.patch",
            "Patch8: malt.patch",
        )

    create_history_with_empty_commit(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "saaz.patch",
        "malt.patch",
    }
    assert sg_path.joinpath(DISTRO_DIR, "saaz.patch").read_text() == ""


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_patch_non_conseq_indices(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, "0.1.0")

    with api_instance_source_git.up.specfile.sections() as sections:
        sections.package[10:10] = (
            "Patch0: amarillo.patch",
            "Patch3: citra.patch",
            "Patch4: saaz.patch",
            "Patch5: malt.patch",
        )

    create_history_with_empty_commit(sg_path)

    malt = sg_path.joinpath("malt")
    malt.write_text("Wheat\n")
    git_add_and_commit(directory=sg_path, message="Weißbier! Summer is coming!")

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    # make sure the patch is inserted AFTER existing patches
    with api_instance_source_git.up.specfile.patches() as patches:
        last_patch = patches[-1]
    assert last_patch.number == 6
    assert last_patch.filename == "0004-Wei-bier-Summer-is-coming.patch"

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "saaz.patch",
        "malt.patch",
        "0004-Wei-bier-Summer-is-coming.patch",
    }
    assert sg_path.joinpath(DISTRO_DIR, "saaz.patch").read_text() == ""


@pytest.mark.parametrize("starting_patch_id", [0, 1, 100])
def test_add_patch_with_patch_id(api_instance_source_git, starting_patch_id):
    """check that patches with patch_id set are added to spec correctly"""
    spec_dir = api_instance_source_git.up.absolute_specfile_dir
    spec: Specfile = api_instance_source_git.up.specfile

    # we want to add this patch to the spec
    good_patch_name1 = "hello.patch"
    # we need to create the patch file so that specfile can find it and process it
    good_patch_path1 = spec_dir.joinpath(good_patch_name1)
    good_patch_path1.write_text("")
    spec.add_patch(good_patch_name1, starting_patch_id)

    with spec.patches() as patches:
        assert patches[0].number == starting_patch_id

    # add another, this time without patch_id
    good_patch_name2 = "hello2.patch"
    good_patch_path2 = spec_dir.joinpath(good_patch_name2)
    good_patch_path2.write_text("")
    spec.add_patch(good_patch_name2)

    # check that index of the second patch is (starting + 1)
    with spec.patches() as patches:
        assert patches[1].number == starting_patch_id + 1

    # and now another with an index lower or equal than the last one and check if
    # an exc is thrown b/c that's not supported
    # to change order of patches (people should reorder the git history instead)
    patch_name = "nope.patch"
    if starting_patch_id <= 1:
        bad_patch_id = starting_patch_id + 1
    else:
        bad_patch_id = starting_patch_id - 1
    with pytest.raises(SourceNumberException):
        spec.add_patch(patch_name, bad_patch_id)


def test_add_patch_first_id_1(api_instance_source_git):
    """check that add_patch sets the first patch id to 1"""
    spec_dir = api_instance_source_git.up.absolute_specfile_dir
    spec: Specfile = api_instance_source_git.up.specfile

    # we want to add this patch to the spec
    good_patch_name1 = "hello.patch"
    # we need to create the patch file so that specfile can find it and process it
    good_patch_path1 = spec_dir.joinpath(good_patch_name1)
    good_patch_path1.write_text("")
    spec.add_patch(good_patch_name1, initial_number=1)

    with spec.patches() as patches:
        assert patches[0].number == 1


def test_srpm_add_patch_with_ids(
    mock_remote_functionality_sourcegit, api_instance_source_git
):
    ref = "0.1.0"
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / DISTRO_DIR, ref)

    create_history_with_patch_ids(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath(DISTRO_DIR).glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "malt.patch",
    }
    with api_instance_source_git.up.specfile.patches() as patches:
        assert patches[0].filename == "amarillo.patch"
        assert patches[0].number == 3
        assert patches[1].filename == "citra.patch"
        assert patches[1].number == 4
        assert patches[2].filename == "malt.patch"
        assert patches[2].number == 100
