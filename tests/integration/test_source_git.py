from packit.utils import cwd
    patches = """
+# switching to amarillo hops
+Patch0001: 0001-switching-to-amarillo-hops.patch
+# actually, let's do citra
+Patch0002: 0002-actually-let-s-do-citra.patch
+Patch0003: 0003-source-change.patch
    assert patches in git_diff

    patch_1_3 = """
+Subject: [PATCH 1/3] switching to amarillo hops
+ hops | 2 +-
+ 1 file changed, 1 insertion(+), 1 deletion(-)
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
+Subject: [PATCH 3/3] source change
+
+---
+ big-source-file.txt | 3 +--
+ 1 file changed, 1 insertion(+), 2 deletions(-)
+
+diff --git a/big-source-file.txt b/big-source-file.txt"""
        in git_diff
    branches = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"], cwd=sg_path
    ).split(b"\n")
    for b in branches:
        if b and b.startswith(b"packit-patches-"):
            raise AssertionError(
                "packit-patches- branch was found - the history shouldn't have been linearized"
            )
    assert set([x.name for x in sg_path.joinpath("fedora").glob("*.patch")]) == {
        "0001-switching-to-amarillo-hops.patch",
        "0002-actually-let-s-do-citra.patch",
    }


def test_srpm_merge_storm(mock_remote_functionality_sourcegit, api_instance_source_git):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path / "fedora")
    create_merge_commit_in_source_git(sg_path, go_nuts=True)
    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref="0.1.0")
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
    assert set([x.name for x in sg_path.joinpath("fedora").glob("*.patch")]) == {
        "0001-MERGE-COMMIT.patch",
        "0002-ugly-merge-commit.patch",
    }