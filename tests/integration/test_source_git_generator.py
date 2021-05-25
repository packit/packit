# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import fileinput
import re
import subprocess
from pathlib import Path
import yaml

import pytest

from packit.constants import CENTOS_DOMAIN, CENTOS_STREAM_GITLAB
from packit.pkgtool import PkgTool
from packit.local_project import LocalProject
from packit.patches import PatchMetadata
from packit.source_git import SourceGitGenerator
from packit.specfile import Specfile
from packit.utils.repo import create_new_repo, clone_centos_9_package
from tests.spellbook import initiate_git_repo

UNIVERSAL_PACKAGE_NAME = "redhat-rpm-config"


@pytest.mark.parametrize(
    "fedora_package, centos_package, branch",
    (
        (UNIVERSAL_PACKAGE_NAME, None, "main"),
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
    create_new_repo(Path(s), [])
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
    assert sgg.local_project.ref == "main"
    assert sgg.local_project.working_dir.joinpath("hops").read_text() == "Cascade\n"
    assert sgg.local_project.git_repo.head.commit.message == "commit with data\n"


@pytest.mark.parametrize(
    "fedora_package, centos_package, branch",
    (("fuse-overlayfs", None, "main"),),
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


def test_create_packit_yaml_upstream_project_url(
    api_instance_source_git, tmp_path: Path
):
    """
    use requre to create a source-git out of it in an empty git repo - packit
    will pull upstream git history
    """
    # requre upstream_project_url
    upstream_project_url = "https://github.com/packit/requre.git"

    # clone dist-git
    pkg = "python-requre"
    dist_git_ref = "6b27ffacda06289ca2d546e15b3c96845243005f"
    dist_git_path = tmp_path.joinpath(pkg)
    source_git_path = tmp_path.joinpath("requre-sg")
    PkgTool().clone(pkg, str(dist_git_path), anonymous=True)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # create src-git
    source_git_path.mkdir()
    create_new_repo(Path(source_git_path), [])
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        upstream_project_url,
        upstream_ref="0.4.0",
        dist_git_path=dist_git_path,
    )
    sgg.create_from_upstream()

    config_file = Path(source_git_path / ".packit.yaml").read_text()
    # black sucks here :/ we are making sure here the yaml looks nice
    assert "patch_generation_ignore_paths:\n- .distro\n" in config_file
    assert "sources:\n- path: requre-0.4.0.tar.gz\n" in config_file
    packit_yaml = yaml.safe_load(config_file)
    assert packit_yaml.get("upstream_project_url") == upstream_project_url


def test_create_packit_yaml_sources(api_instance_source_git, tmp_path: Path):
    """
    use requre to create a source-git out of it in an empty git repo - packit
    will pull upstream git history
    """
    # requre lookaside_cache_url
    requre_tar_url = (
        "https://src.fedoraproject.org/repo/pkgs/rpms/python-requre/"
        "requre-0.4.0.tar.gz/sha512/85293577f56e19dd0fad13bb5e118ac2ab39d7"
        "570d640a754b9d8d8054078c89c949d4695ef018915b17a2f2428f1635032352d"
        "cf3c9a036a2d633013cc35dd9/requre-0.4.0.tar.gz"
    )
    requre_tar_path = "requre-0.4.0.tar.gz"

    # clone dist-git
    pkg = "python-requre"
    dist_git_ref = "6b27ffacda06289ca2d546e15b3c96845243005f"
    dist_git_path = tmp_path.joinpath(pkg)
    source_git_path = tmp_path.joinpath("requre-sg")
    PkgTool().clone(pkg, str(dist_git_path), anonymous=True)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # create src-git
    source_git_path.mkdir()
    create_new_repo(Path(source_git_path), [])
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        "https://github.com/packit/requre",
        upstream_ref="0.4.0",
        dist_git_path=dist_git_path,
    )
    sgg.create_from_upstream()

    config_file = Path(source_git_path / ".packit.yaml").read_text()
    # black sucks here :/ we are making sure here the yaml looks nice
    assert "patch_generation_ignore_paths:\n- .distro\n" in config_file
    assert "sources:\n- path: requre-0.4.0.tar.gz\n" in config_file
    packit_yaml = yaml.safe_load(config_file)
    assert packit_yaml.get("sources")
    assert len(packit_yaml["sources"]) > 0
    assert packit_yaml["sources"][0].get("url")
    assert packit_yaml["sources"][0].get("path")

    assert packit_yaml["sources"][0]["url"] == requre_tar_url
    assert packit_yaml["sources"][0]["path"] == requre_tar_path


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
    PkgTool().clone(pkg, str(dist_git_path), anonymous=True)
    dg_lp = LocalProject(working_dir=dist_git_path)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # add a patch in there
    spec = Specfile(dist_git_path / f"{pkg}.spec", sources_dir=dist_git_path)
    patch_name = "hello.patch"
    patch_path = dist_git_path.joinpath(patch_name)
    patch_path.write_text(REQURE_PATCH)
    patch = PatchMetadata(name=patch_name, path=patch_path, present_in_specfile=False)
    spec.add_patch(patch)
    dg_lp.stage()
    dg_lp.commit("add the hello patch")
    subprocess.check_call(["fedpkg", "prep"], cwd=dist_git_path)

    # create src-git
    source_git_path.mkdir()
    create_new_repo(Path(source_git_path), [])
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

    # verify the archive is not committed in the source-git
    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                f"{sgg.dist_git.source_git_downstream_suffix}/{spec.get_archive()}",
            ],
            cwd=source_git_path,
        )
    assert exc.value.returncode == 1


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
    PkgTool().clone(pkg, str(dist_git_path), anonymous=True)
    dg_lp = LocalProject(working_dir=dist_git_path)

    # check out specific ref
    subprocess.check_call(["git", "reset", "--hard", dist_git_ref], cwd=dist_git_path)

    # add a patch in there
    spec = Specfile(dist_git_path / f"{pkg}.spec", sources_dir=dist_git_path)
    patch_name = "hello.patch"
    patch_path = dist_git_path.joinpath(patch_name)
    patch_path.write_text(REQURE_PATCH)
    patch = PatchMetadata(name=patch_name, path=patch_path, present_in_specfile=False)
    spec.add_patch(patch)
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


@pytest.mark.slow
@pytest.mark.parametrize(
    "dist_git_branch,upstream_ref", (("c8s", "cronie-1.5.2"), ("c9s", "cronie-1.5.5"))
)
def test_centos_cronie(
    dist_git_branch, upstream_ref, api_instance_source_git, tmp_path: Path
):
    source_git_path = tmp_path.joinpath("cronie-sg")
    # create src-git
    source_git_path.mkdir()
    create_new_repo(source_git_path, [])
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        "https://github.com/cronie-crond/cronie",
        upstream_ref=upstream_ref,
        centos_package="cronie",
        dist_git_branch=dist_git_branch,
    )
    sgg.create_from_upstream()

    if dist_git_branch == "c8s":
        assert CENTOS_DOMAIN in sgg.dist_git.local_project.git_url
    else:
        assert CENTOS_STREAM_GITLAB in sgg.dist_git.local_project.git_url

    # verify it
    subprocess.check_call(["packit", "srpm"], cwd=source_git_path)
    srpm_path = list(source_git_path.glob("cronie-*.src.rpm"))[0]
    assert srpm_path.is_file()


@pytest.mark.slow
@pytest.mark.parametrize("apply_option", ("git", "git_am"))
def test_acl_with_git_git_am(apply_option, api_instance_source_git, tmp_path: Path):
    """manipulate acl's dist-git to use -Sgit and -Sgit_am so we can verify it works"""
    dist_git_branch = "c9s"
    package_name = "acl"
    source_git_path = tmp_path.joinpath("acl-sg")
    # dist-git tools expect: dir name == package name
    dist_git_path = tmp_path.joinpath(package_name)

    # create src-git
    source_git_path.mkdir()
    create_new_repo(source_git_path, [])

    # fetch dist-git and change %autosetup
    clone_centos_9_package(
        package_name,
        dist_git_path=dist_git_path,
        branch=dist_git_branch,
    )
    for line in fileinput.input(
        dist_git_path.joinpath(f"{package_name}.spec"), inplace=True
    ):
        if "%autosetup" in line:
            line = f"%autosetup -p1 -S{apply_option}"
        print(line, end="")  # \n would make double-newlines here

    # run conversion
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        api_instance_source_git.config,
        "https://git.savannah.nongnu.org/git/acl.git",
        upstream_ref="v2.3.1",
        centos_package=package_name,
        dist_git_branch=dist_git_branch,
        dist_git_path=dist_git_path,
    )
    sgg.create_from_upstream()

    # verify the patch commit has metadata
    patch_commit_message = sgg.local_project.git_repo.head.commit.message
    assert "present_in_specfile: true" in patch_commit_message
    assert "patch_name: 0001-acl-2.2.53-test-runwrapper.patch" in patch_commit_message
    assert re.findall(r"patch_id: \d", patch_commit_message)
