# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
import yaml

from flexmock import flexmock
from pathlib import Path

from packit.constants import SRC_GIT_CONFIG, DISTRO_DIR
from packit.exceptions import PackitException
from packit.source_git import SourceGitGenerator
from packit.pkgtool import PkgTool

from tests.integration.conftest import HELLO_RELEASE


def test_upstream_ref_not_at_head(hello_source_git_repo, hello_dist_git_repo):
    """Initializing a source-git repo fails, if the upstream_ref which
    should be the starting point of the downstream changes is not at
    the HEAD of the source-git repo.
    """
    readme = Path(hello_source_git_repo.working_dir, "README.md")
    with open(readme, "a") as fp:
        fp.write("\nSome new thing\n")
    hello_source_git_repo.git.add("README.md")
    hello_source_git_repo.git.commit(message="Add a new thing")

    sgg = SourceGitGenerator(
        config=flexmock(),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
    )
    with pytest.raises(PackitException) as ex:
        sgg.create_from_upstream()
    assert "not pointing to the current HEAD" in str(ex.value)


def test_not_using_autosetup(hello_source_git_repo, hello_dist_git_repo):
    """Initializing a source-git repo for packages which don't use
    %autosetup in their specfile is currently not supported.
    """
    spec = Path(hello_dist_git_repo.working_dir, "hello.spec")
    content = spec.read_text().replace("%autosetup", "%setup")
    spec.write_text(content)
    hello_dist_git_repo.git.add("hello.spec")
    hello_dist_git_repo.git.commit(message="Use %setup")

    sgg = SourceGitGenerator(
        config=flexmock(),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
    )
    with pytest.raises(PackitException) as ex:
        sgg.create_from_upstream()
    assert "not using %autosetup" in str(ex.value)


def modify_file(path: Path):
    content = path.read_text() + "\n# some change\n"
    path.write_text(content)


def create_file(path: Path):
    Path(path.parent, "new.file").touch()


@pytest.mark.parametrize("change", [modify_file, create_file])
def test_dist_git_not_pristine(hello_source_git_repo, hello_dist_git_repo, change):
    """Initialization fails if the dist-git working directory is not
    pristine, has changes and/or untracked files, in order to avoid
    tracking files in source-git which are not part of the dist-git repo
    and history.
    """
    change(Path(hello_dist_git_repo.working_dir, "hello.spec"))

    sgg = SourceGitGenerator(
        config=flexmock(),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
        pkg_name="hello",
    )
    with pytest.raises(PackitException) as ex:
        sgg.create_from_upstream()
    assert "is not pristine" in str(ex.value)


def download_sources(from_repo, to_repo):
    def funk():
        from_repo.git.archive(
            HELLO_RELEASE,
            format="tar.gz",
            prefix=f"hello-{HELLO_RELEASE}/",
            output=f"{to_repo.working_dir}/hello-{HELLO_RELEASE}.tar.gz",
        )

    return funk


def check_source_git_config(source_git_config):
    assert source_git_config["upstream_project_url"] == "https://example.com/hello.git"
    assert source_git_config["upstream_ref"] == HELLO_RELEASE
    assert source_git_config["downstream_package_name"] == "hello"
    assert source_git_config["specfile_path"] == ".distro/hello.spec"
    assert source_git_config["patch_generation_ignore_paths"] == [DISTRO_DIR]
    assert source_git_config["sync_changelog"] is True
    assert source_git_config["files_to_sync"] == [
        {
            "src": ".distro/",
            "dest": ".",
            "delete": True,
            "filters": [
                "protect .git*",
                "protect sources",
                f"exclude {SRC_GIT_CONFIG}",
                "exclude .gitignore",
            ],
        }
    ]
    assert source_git_config["sources"][0]["path"] == f"hello-{HELLO_RELEASE}.tar.gz"


@pytest.mark.skipif(
    # on rawhide the version can contain letters:
    # >>> yaml.__version__
    # '6.0b1'
    list(map(int, yaml.__version__[:3].split("."))) < [5, 1],
    reason="Requires PyYAML 5.1 or higher.",
)
def test_create_from_upstream_no_patch(hello_source_git_repo, hello_dist_git_repo):
    """A source-git repo is properly initialized from a dist-git repo.
    - No downstream patches.
    """
    spec = Path(hello_dist_git_repo.working_dir, "hello.spec")
    content = [
        line for line in spec.read_text().splitlines() if not line.startswith("Patch")
    ]
    spec.write_text("\n".join(content) + "\n")
    Path(hello_dist_git_repo.working_dir, "turn-into-fedora.patch").unlink()
    hello_dist_git_repo.git.add(".")
    hello_dist_git_repo.git.commit(message="Remove the patch")

    flexmock(
        PkgTool, sources=download_sources(hello_source_git_repo, hello_dist_git_repo)
    )
    sgg = SourceGitGenerator(
        config=flexmock(fas_user=None, pkg_tool="fedpkg"),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
        pkg_name="hello",
    )
    sgg.create_from_upstream()
    source_git_config = yaml.safe_load(
        Path(hello_source_git_repo.working_dir, DISTRO_DIR, SRC_GIT_CONFIG).read_text()
    )
    check_source_git_config(source_git_config)
    assert source_git_config["patch_generation_patch_id_digits"] == 1
    assert (
        f"\nFrom-dist-git-commit: {hello_dist_git_repo.head.commit.hexsha}\n"
        in hello_source_git_repo.head.commit.message
    )


@pytest.mark.skipif(
    # on rawhide the version can contain letters:
    list(map(int, yaml.__version__[:3].split("."))) < [5, 1],
    reason="Requires PyYAML 5.1 or higher.",
)
def test_create_from_upstream_with_patch(hello_source_git_repo, hello_dist_git_repo):
    """A source-git repo is properly initialized from a dist-git repo.
    - A few downstream patches.
    """
    flexmock(
        PkgTool, sources=download_sources(hello_source_git_repo, hello_dist_git_repo)
    )
    sgg = SourceGitGenerator(
        config=flexmock(fas_user=None, pkg_tool="fedpkg"),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
        pkg_name="hello",
    )
    sgg.create_from_upstream()
    source_git_config = yaml.safe_load(
        Path(hello_source_git_repo.working_dir, DISTRO_DIR, SRC_GIT_CONFIG).read_text()
    )
    check_source_git_config(source_git_config)
    assert source_git_config["patch_generation_patch_id_digits"] == 4

    assert (
        Path(hello_source_git_repo.working_dir, DISTRO_DIR, ".gitignore").read_text()
        == """\
# Reset gitignore rules
!*
"""
    )
    assert not Path(hello_source_git_repo.working_dir, DISTRO_DIR, "sources").exists()
    assert not Path(hello_source_git_repo.working_dir, DISTRO_DIR, ".git").exists()

    assert (
        "Hello Fedora Linux"
        in Path(hello_source_git_repo.working_dir, "hello.rs").read_text()
    )

    commit_messsage_lines = hello_source_git_repo.commit("HEAD~2").message.splitlines()
    assert "Patch-name: turn-into-fedora.patch" in commit_messsage_lines
    assert "Patch-id: 1" in commit_messsage_lines
    assert "Patch-status: |" in commit_messsage_lines
    assert (
        f"From-dist-git-commit: {hello_dist_git_repo.head.commit.hexsha}"
        in commit_messsage_lines
    )

    commit_messsage_lines = hello_source_git_repo.commit("HEAD~1").message.splitlines()
    assert "Patch-name: from-git.patch" in commit_messsage_lines
    assert "Patch-id: 2" in commit_messsage_lines
    assert "Patch-status: |" in commit_messsage_lines
    assert (
        f"From-dist-git-commit: {hello_dist_git_repo.head.commit.hexsha}"
        in commit_messsage_lines
    )


@pytest.mark.skipif(
    # on rawhide the version can contain letters:
    # >>> yaml.__version__
    # '6.0b1'
    list(map(int, yaml.__version__[:3].split("."))) < [5, 1],
    reason="Requires PyYAML 5.1 or higher.",
)
def test_create_from_upstream_not_require_autosetup(
    hello_source_git_repo, hello_dist_git_repo
):
    """A source-git repo is properly initialized from a dist-git repo.
    - No downstream patches.
    """
    spec = Path(hello_dist_git_repo.working_dir, "hello.spec")
    content = spec.read_text().replace(
        "%autosetup", "%setup -q -n hello-%{version}\n%autopatch -p1"
    )
    spec.write_text(content)
    hello_dist_git_repo.git.add("hello.spec")
    hello_dist_git_repo.git.commit(message="Use %setup")

    flexmock(
        PkgTool, sources=download_sources(hello_source_git_repo, hello_dist_git_repo)
    )
    sgg = SourceGitGenerator(
        config=flexmock(fas_user=None, pkg_tool="fedpkg"),
        source_git=hello_source_git_repo,
        dist_git=hello_dist_git_repo,
        upstream_ref=HELLO_RELEASE,
        pkg_name="hello",
        ignore_missing_autosetup=True,
    )
    sgg.create_from_upstream()
    source_git_config = yaml.safe_load(
        Path(hello_source_git_repo.working_dir, DISTRO_DIR, SRC_GIT_CONFIG).read_text()
    )
    check_source_git_config(source_git_config)
    assert source_git_config["patch_generation_patch_id_digits"] == 4

    assert (
        Path(hello_source_git_repo.working_dir, DISTRO_DIR, ".gitignore").read_text()
        == """\
# Reset gitignore rules
!*
"""
    )
    assert not Path(hello_source_git_repo.working_dir, DISTRO_DIR, "sources").exists()
    assert not Path(hello_source_git_repo.working_dir, DISTRO_DIR, ".git").exists()

    assert (
        "Hello Fedora Linux"
        in Path(hello_source_git_repo.working_dir, "hello.rs").read_text()
    )

    commit = hello_source_git_repo.commit("HEAD~2")
    commit_messsage_lines = commit.message.splitlines()
    assert "Patch-name: turn-into-fedora.patch" in commit_messsage_lines
    assert "Patch-id: 1" in commit_messsage_lines
    assert "Patch-status: |" in commit_messsage_lines
    assert (
        f"From-dist-git-commit: {hello_dist_git_repo.head.commit.hexsha}"
        in commit_messsage_lines
    )
    # Author of a non-git-am patch is the one who was the original author
    # of the patch-file in dist-git.
    assert commit.author.name == "Engin Eer"
    assert commit.author.email == "eer@redhat.com"

    commit = hello_source_git_repo.commit("HEAD~1")
    commit_messsage_lines = commit.message.splitlines()
    assert "Patch-name: from-git.patch" in commit_messsage_lines
    assert "Patch-name: from-another-git.patch" not in commit_messsage_lines
    assert "Patch-id: 2" in commit_messsage_lines
    assert "Patch-status: |" in commit_messsage_lines
    assert (
        f"From-dist-git-commit: {hello_dist_git_repo.head.commit.hexsha}"
        in commit_messsage_lines
    )
    assert commit.author.name == "A U Thor"
    assert commit.author.email == "thor@redhat.com"
