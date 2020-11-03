# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

import subprocess
from pathlib import Path

import pytest

from packit.specfile import Specfile
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
)


def test_basic_local_update_without_patching(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_patching,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    api_instance_source_git.sync_release(
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref="0.1.0",
    )

    assert (distgit / TARBALL_NAME).is_file()
    spec = Specfile(distgit / "beer.spec")
    assert spec.get_version() == "0.1.0"


@pytest.mark.parametrize("ref", [None, "0.1.0", "0.1*", "0.*"])
def test_basic_local_update_empty_patch(
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
    ref,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)
    api_instance_source_git.sync_release(
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref=ref,
    )

    assert (distgit / TARBALL_NAME).is_file()
    spec = Specfile(distgit / "beer.spec")
    assert spec.get_version() == "0.1.0"

    spec_package_section = ""
    for section in spec.spec_content.sections:
        if "%package" in section[0]:
            spec_package_section += "\n".join(section[1])
    assert "# PATCHES FROM SOURCE GIT" not in spec_package_section
    assert not spec.patches["applied"]
    assert not spec.patches["not_applied"]


def test_basic_local_update_patch_content(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

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
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    assert (
        """
-Version:        0.0.0
+Version:        0.1.0"""
        in git_diff
    )

    patches = """
+# PATCHES FROM SOURCE GIT:
+
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001: 0001-switching-to-amarillo-hops.patch
+
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002: 0002-actually-let-s-do-citra.patch
+
+# source change
+# Author: Packit Test Suite <test@example.com>
+Patch0003: 0003-source-change.patch
+
+
 %description
"""
    assert patches in git_diff

    assert "Patch0004:" not in git_diff

    assert (
        """ - 0.1.0-1
+- commit with data (Packit Test Suite)
+- empty commit #2 (Packit Test Suite)
+- empty commit #1 (Packit Test Suite)
+- empty commit #0 (Packit Test Suite)
+
 * Sun Feb 24 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.0.0-1
 - No brewing, yet."""
        in git_diff
    )

    # direct diff in the synced file
    assert (
        """diff --git a/.packit.yaml b/.packit.yaml
new file mode 100644"""
        in git_diff
    )

    assert (
        """
--- /dev/null
+++ b/.packit.yaml"""
        in git_diff
    )

    # diff of the synced file should not be in the patch
    assert (
        """
+diff --git a/.packit.yaml b/.packit.yaml
+new file mode 100644"""
        not in git_diff
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
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

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
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# PATCHES FROM SOURCE GIT:
+
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001: 0001-switching-to-amarillo-hops.patch
+
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002: 0002-actually-let-s-do-citra.patch
+
+# source change
+# Author: Packit Test Suite <test@example.com>
+# Few words for info.
+Patch0003: testing.patch
+
+
 %description
"""
    assert patches in git_diff


def test_basic_local_update_patch_content_with_metadata_and_patch_ignored(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

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
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# PATCHES FROM SOURCE GIT:
+
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001: 0001-switching-to-amarillo-hops.patch
+
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002: 0002-actually-let-s-do-citra.patch
+
+
 %description
"""
    assert patches in git_diff


def test_basic_local_update_patch_content_with_downstream_patch(
    sourcegit_and_remote,
    distgit_and_remote,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    mock_spec_download_remote_s(distgit)

    create_merge_commit_in_source_git(sourcegit)

    source_file = sourcegit / "ignored_file.txt"
    source_file.write_text(" And I am sad.")
    git_add_and_commit(directory=sourcegit, message="make a file sad")

    api_instance_source_git.sync_release(
        dist_git_branch="master",
        version="0.1.0",
        use_local_content=True,
        upstream_ref="0.1.0",
    )

    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    patches = """
+# PATCHES FROM SOURCE GIT:
+
+# switching to amarillo hops
+# Author: Packit Test Suite <test@example.com>
+Patch0001: 0001-switching-to-amarillo-hops.patch
+
+# actually, let's do citra
+# Author: Packit Test Suite <test@example.com>
+Patch0002: 0002-actually-let-s-do-citra.patch
+
+
 %description
"""
    assert patches in git_diff


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm(mock_remote_functionality_sourcegit, api_instance_source_git, ref):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")
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
    assert {x.name for x in sg_path.joinpath("fedora").glob("*.patch")} == {
        "0001-switching-to-amarillo-hops.patch",
        "0002-actually-let-s-do-citra.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_merge_storm(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")
    create_merge_commit_in_source_git(sg_path, go_nuts=True)
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
    assert {x.name for x in sg_path.joinpath("fedora").glob("*.patch")} == {
        "0001-MERGE-COMMIT.patch",
        "0002-ugly-merge-commit.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_git_am(mock_remote_functionality_sourcegit, api_instance_source_git, ref):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")

    api_instance_source_git.up.specfile.spec_content.section("%package")[10:10] = (
        "Patch1: citra.patch",
        "Patch2: malt.patch",
        "Patch8: 0001-m04r-malt.patch",
    )
    autosetup_line = api_instance_source_git.up.specfile.spec_content.section("%prep")[
        0
    ]
    autosetup_line = autosetup_line.replace("-S patch", "-S git_am")
    api_instance_source_git.up.specfile.spec_content.section("%prep")[
        0
    ] = autosetup_line
    api_instance_source_git.up.specfile.save()

    create_git_am_style_history(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath("fedora").glob("*.patch")} == {
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
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")

    api_instance_source_git.up.specfile.spec_content.section("%package")[10:10] = (
        "Patch1: amarillo.patch",
        "Patch2: citra.patch",
        "Patch8: malt.patch",
    )
    api_instance_source_git.up.specfile.spec_content.section("%prep")[0:2] = [
        "%setup -n %{upstream_name}-%{version}",
        "%patch1 -p1",
        "%patch2 -p0",
        "%patch8 -p1",
    ]
    api_instance_source_git.up.specfile.save()

    create_patch_mixed_history(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath("fedora").glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "malt.patch",
    }


@pytest.mark.parametrize("ref", ["0.1.0", "0.1*", "0.*"])
def test_srpm_empty_patch(
    mock_remote_functionality_sourcegit, api_instance_source_git, ref
):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")

    api_instance_source_git.up.specfile.spec_content.section("%package")[10:10] = (
        "Patch1: amarillo.patch",
        "Patch2: citra.patch",
        "Patch5: saaz.patch",
        "Patch8: malt.patch",
    )
    api_instance_source_git.up.specfile.save()

    create_history_with_empty_commit(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref=ref)

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert {x.name for x in sg_path.joinpath("fedora").glob("*.patch")} == {
        "amarillo.patch",
        "citra.patch",
        "saaz.patch",
        "malt.patch",
    }
    assert sg_path.joinpath("fedora", "saaz.patch").read_text() == ""
