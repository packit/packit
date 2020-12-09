# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import subprocess
from pathlib import Path

import pytest

from packit.fedpkg import FedPKG
from packit.local_project import LocalProject
from packit.patches import PatchMetadata
from packit.source_git import SourceGitGenerator
from packit.specfile import Specfile
from tests.spellbook import initiate_git_repo

UNIVERSAL_PACKAGE_NAME = "redhat-rpm-config"


@pytest.mark.parametrize(
    "fedora_package, centos_package, branch",
    (
        (UNIVERSAL_PACKAGE_NAME, None, "master"),
        (None, UNIVERSAL_PACKAGE_NAME, "c8s"),
    ),
)
def test_distgit_cloning(
    api_instance_source_git, fedora_package, centos_package, branch, tmp_path: Path
):
    sgg = SourceGitGenerator(
        api_instance_source_git.upstream_local_project,
        api_instance_source_git.config,
        # yes, this is the upstream repo
        f"https://src.fedoraproject.org/rpms/{UNIVERSAL_PACKAGE_NAME}",
        fedora_package=fedora_package,
        centos_package=centos_package,
        dist_git_branch=branch,
        tmpdir=tmp_path,
    )
    sgg._get_dist_git()
    assert tmp_path.joinpath(UNIVERSAL_PACKAGE_NAME, ".git").is_dir()


# TODO: test different refs: tag, branch, commit hash
def test_fetch_upstream_ref(api_instance_source_git, tmp_path: Path):
    tag = "1.0.0"
    s = tmp_path.joinpath("s")
    u = tmp_path.joinpath("u")
    u.mkdir()
    subprocess.check_call(["git", "init", str(s)])
    initiate_git_repo(u, tag=tag)
    sgg = SourceGitGenerator(
        LocalProject(working_dir=s),
        api_instance_source_git.config,
        str(u),
        upstream_ref=tag,
        centos_package="x",
    )

    sgg._pull_upstream_ref()

    assert s.joinpath(".git").is_dir()
    assert sgg.local_project.ref == "master"
    assert sgg.local_project.working_dir.joinpath("hops").read_text() == "Cascade\n"
    assert sgg.local_project.git_repo.head.commit.message == "commit with data\n"


@pytest.mark.parametrize(
    "fedora_package, centos_package, branch",
    (("fuse-overlayfs", None, "master"),),
)
def test_run_prep(
    api_instance_source_git, fedora_package, centos_package, branch, tmp_path: Path
):
    sgg = SourceGitGenerator(
        api_instance_source_git.upstream_local_project,
        api_instance_source_git.config,
        f"https://github.com/containers/{fedora_package}",
        fedora_package=fedora_package,
        centos_package=centos_package,
        dist_git_branch=branch,
        tmpdir=tmp_path,
    )
    assert sgg.primary_archive.exists()  # making sure this is downloaded
    sgg._run_prep()
    build_dir = sgg.dist_git.local_project.working_dir.joinpath("BUILD")
    assert build_dir.exists()
    project_dir = next(build_dir.glob("fuse-overlayfs-*"))
    assert project_dir.joinpath(".git")


REQURE_PATCH = r"""\
diff --git a/README.md b/README.md
index 17e9e85..99ef68c 100644
--- a/README.md
+++ b/README.md
@@ -15,3 +15,5 @@ back
 - Used for testing [packit-service](https://github.com/packit-service) organization projects
   - ogr
   - packit
+
+Hello!
"""


def test_create_srcgit_requre_clean(api_instance_source_git, tmp_path: Path):
    """
    use requre to create a source-git out of it in an empty git repo - packit
    will pull upstream git history
    """
    # clone dist-git
    pkg = "python-requre"
    dist_git_ref = "6b27ffacda06289ca2d546e15b3c96845243005f"
    dist_git_path = tmp_path.joinpath(pkg)
    source_git_path = tmp_path.joinpath("requre-sg")
    FedPKG().clone(pkg, str(dist_git_path), anonymous=True)
    dg_lp = LocalProject(working_dir=dist_git_path)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # add a patch in there
    spec = Specfile(dist_git_path / f"{pkg}.spec", sources_dir=dist_git_path)
    patch_name = "hello.patch"
    patch_path = dist_git_path.joinpath(patch_name)
    patch_path.write_text(REQURE_PATCH)
    patch = PatchMetadata(name=patch_name, path=patch_path, present_in_specfile=False)
    spec.add_patches([patch])
    dg_lp.stage()
    dg_lp.commit("add the hello patch")
    subprocess.check_call(["fedpkg", "prep"], cwd=dist_git_path)

    # create src-git
    source_git_path.mkdir()
    subprocess.check_call(["git", "init", str(source_git_path)])
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        "https://github.com/packit/requre",
        upstream_ref="0.4.0",
        dist_git_path=dist_git_path,
    )
    sgg.create_from_upstream()

    # verify it
    subprocess.check_call(["packit", "srpm"], cwd=source_git_path)
    srpm_path = list(source_git_path.glob("python-requre-0.4.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    # requre needs sphinx, so SRPM is fine


def test_create_srcgit_requre_populated(api_instance_source_git, tmp_path: Path):
    """
    use requre to create a source-git out of it in a branch with upstream git history
    - this should only layer downstream changes on top
    """
    # clone dist-git
    pkg = "python-requre"
    dist_git_ref = "6b27ffacda06289ca2d546e15b3c96845243005f"
    dist_git_path = tmp_path.joinpath(pkg)
    source_git_path = tmp_path.joinpath("requre-sg")
    FedPKG().clone(pkg, str(dist_git_path), anonymous=True)
    dg_lp = LocalProject(working_dir=dist_git_path)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # add a patch in there
    spec = Specfile(dist_git_path / f"{pkg}.spec", sources_dir=dist_git_path)
    patch_name = "hello.patch"
    patch_path = dist_git_path.joinpath(patch_name)
    patch_path.write_text(REQURE_PATCH)
    patch = PatchMetadata(name=patch_name, path=patch_path, present_in_specfile=False)
    spec.add_patches([patch])
    dg_lp.stage()
    dg_lp.commit("add the hello patch")
    subprocess.check_call(["fedpkg", "prep"], cwd=dist_git_path)

    # create src-git
    source_git_path.mkdir()
    subprocess.check_call(
        ["git", "clone", "https://github.com/packit/requre", str(source_git_path)]
    )
    subprocess.check_call(
        ["git", "checkout", "-B", "source-git-0.4.0", "0.4.0"], cwd=source_git_path
    )
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        dist_git_path=dist_git_path,
    )
    sgg.create_from_upstream()

    # verify it
    subprocess.check_call(["packit", "srpm"], cwd=source_git_path)
    srpm_path = list(source_git_path.glob("python-requre-0.4.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    # requre needs sphinx, so SRPM is fine
