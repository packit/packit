# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Tests for Upstream class
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock
from ogr import GithubService

import packit
from packit.actions import ActionName
from packit.config import Config, get_local_package_config
from packit.exceptions import PackitSRPMException
from packit.local_project import LocalProject
from packit.upstream import Archive, Upstream, SRPMBuilder
from packit.utils.commands import cwd
from packit.utils.repo import create_new_repo

from tests.spellbook import (
    EMPTY_CHANGELOG,
    UPSTREAM_MACRO_IN_SOURCE,
    initiate_git_repo,
    get_test_config,
    build_srpm,
)


def test_get_spec_version(upstream_instance):
    u, ups = upstream_instance
    assert ups.get_specfile_version() == "0.1.0"


@pytest.mark.parametrize(
    "tag, tag_template, expected_output",
    [
        pytest.param(
            "1.0.0",
            "{version}",
            "1.0.0",
            id="no_command-pure_version-valid_template",
        ),
        pytest.param(
            "test-1.0.0",
            "test-{version}",
            "1.0.0",
            id="no_command-valid_tag-valid_template",
        ),
    ],
)
def test_get_current_version(tag, tag_template, expected_output, upstream_instance):
    u, ups = upstream_instance
    flexmock(ups)
    ups.package_config.upstream_tag_template = tag_template
    # just to simulate current_vesrsion_command set/notset
    ups.should_receive("get_last_tag").and_return(tag)

    assert ups.get_current_version() == expected_output


@pytest.mark.parametrize(
    "m_v,exp",
    (
        ("1.1000.1000000", "1.1000.1000000"),
        (None, "0.1.0"),
        ("0.0.3", "0.1.0"),
        ("176", "176"),
    ),
)
def test_get_version(upstream_instance, m_v, exp):
    u, ups = upstream_instance
    flexmock(packit.upstream, get_upstream_version=lambda _: m_v)

    assert ups.get_version() == exp

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    assert ups.get_current_version() == "0.1.0"


def test_get_version_macro(upstream_instance):
    u, ups = upstream_instance

    data = "import setuptools \nsetuptools.setup(version='1')"
    setup_path = u.joinpath("setup.py")
    with open(u.joinpath("setup.py"), "w+") as setup:
        setup.write(data)

    data = u.joinpath("beer.spec").read_text()
    data = data.replace("0.1.0", "%(python3 " + str(setup_path) + " --version)")
    with open(u.joinpath("beer.spec"), "w") as f:
        f.write(data)

    assert ups.get_specfile_version() == "1"


def test_set_spec_ver(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.specfile.version = new_ver
    ups.specfile.add_changelog_entry("- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "- asdqwe" in u.joinpath("beer.spec").read_text()


def test_set_spec_macro_source(tmp_path):
    u_remote_path = tmp_path / "upstream_remote"
    u_remote_path.mkdir(parents=True, exist_ok=True)

    create_new_repo(u_remote_path, ["--bare"])

    u = tmp_path / "upstream_git"
    shutil.copytree(UPSTREAM_MACRO_IN_SOURCE, u)
    initiate_git_repo(u, tag="0.1.0")

    with cwd(tmp_path):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        lp = LocalProject(working_dir=u)

        ups = Upstream(c, pc, lp)

    expected_sources = ups.specfile.sources
    new_ver = "1.2.3"
    ups.specfile.version = new_ver
    ups.specfile.add_changelog_entry("- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert ups.specfile.sources == expected_sources

    expected_sources = ups.specfile.sources
    new_rel = "121"
    ups.specfile.release = new_rel

    assert ups.specfile.release == new_rel
    assert ups.specfile.sources == expected_sources


def test_set_spec_ver_empty_changelog(tmp_path):
    u_remote_path = tmp_path / "upstream_remote"
    u_remote_path.mkdir(parents=True, exist_ok=True)

    create_new_repo(u_remote_path, ["--bare"])

    u = tmp_path / "upstream_git"
    shutil.copytree(EMPTY_CHANGELOG, u)
    initiate_git_repo(u, tag="0.1.0")

    with cwd(tmp_path):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        lp = LocalProject(working_dir=u)

        ups = Upstream(c, pc, lp)

    new_ver = "1.2.3"
    ups.specfile.version = new_ver
    ups.specfile.add_changelog_entry("- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "%changelog" not in u.joinpath("beer.spec").read_text()


def change_source_ext(upstream, extension):
    with upstream.specfile.sources() as sources:
        for source in sources:
            source.location = (
                source.location.rstrip("".join(Path(source.location).suffixes))
                + extension
            )


@pytest.mark.parametrize(
    "extension", [".tar.gz", ".tar.bz2"], ids=[".tar.gz", ".tar.bz2"]
)
def test_create_archive(upstream_instance, extension):
    u, ups = upstream_instance
    change_source_ext(ups, extension)

    ups.create_archive()

    assert u.glob(f"*{extension}")

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()

    # we enforce .tar.gz now
    assert len(list(u.glob("*.tar.gz"))) == 1


@pytest.mark.parametrize(
    "with_create_archive_action",
    (False, True),
)
def test_create_archive_spec_subdir(upstream_instance, with_create_archive_action):
    """test archive creation when an archive is in root, but spec is in a subdir"""
    u, ups = upstream_instance

    if with_create_archive_action:
        archive_path = u.joinpath("beer.tar.gz")
        ups.package_config.actions[ActionName.create_archive] = [
            [
                "git",
                "archive",
                "--output",
                str(archive_path),
                "--prefix",
                f"{u.name}/",
                "HEAD",
            ],
            ["echo", str(archive_path)],
        ]

    packaging_dir = u / "packaging"
    packaging_dir.mkdir()
    spec_path = packaging_dir / "some.spec"
    spec_path.write_text("asd")
    ups._specfile_path = spec_path

    ups.create_archive()

    archives_in_packaging_dir = list(packaging_dir.glob("*.tar.gz"))
    assert len(archives_in_packaging_dir) == 1

    if with_create_archive_action:
        assert archives_in_packaging_dir[0].is_symlink()
        assert len(list(ups.local_project.working_dir.glob("*.tar.gz"))) == 1


def test_create_uncommon_archive(upstream_instance):
    u, ups = upstream_instance
    change_source_ext(ups, ".cpio")
    ups.create_archive()
    # we enforce .tar.gz now
    assert len(list(u.glob("*.tar.gz"))) == 1


def test_fix_spec(upstream_instance):
    u, ups = upstream_instance

    ups.package_config.upstream_package_name = "beer"
    archive = ups.create_archive()
    ups.fix_spec(
        archive=archive,
        version="_1.2.3",
        commit="_abcdef123",
        release_suffix="1.20200710085501945230.master.0.g133ff39",
    )

    release = ups.specfile.expanded_release
    # 1.20200710085501945230.master.0.g133ff39
    assert re.match(r"\d\.\d{20}\.\w+\.\d+\.g\w{7}", release)


def test_fix_spec_persists(upstream_instance):
    """verify that changing specfile in fix_spec action persists"""
    _, upstream = upstream_instance
    upstream.package_config.actions = {
        ActionName.fix_spec: "sed -i 's/^Version:.*$/Version: 1.0.0/' beer.spec"
    }
    SRPMBuilder(upstream)._fix_specfile_to_use_local_archive(
        "archive.tar.gz", bump_version=False, release_suffix="1.%dist"
    )

    assert upstream.specfile.version == "1.0.0"


@pytest.mark.parametrize(
    "spec_source_id, expected_line",
    [
        pytest.param(
            "Source",
            r"Source:\s*fixed-source-archive.tar.gz",
            id="Source",
        ),
        pytest.param(
            "Source0",
            r"Source:\s*fixed-source-archive.tar.gz",
            id="Source0",
        ),
        pytest.param(
            "Source100",
            r"Source100:\s*fixed-source-archive.tar.gz",
            id="Source100",
        ),
    ],
)
def test__fix_spec_source(upstream_instance, spec_source_id, expected_line):
    u, ups = upstream_instance

    data = u.joinpath("beer.spec").read_text()
    data = re.sub(r"(Source:.*)", "\\1\nSource100: extra-sources.tar.gz", data)
    with open(u.joinpath("beer.spec"), "w") as f:
        f.write(data)

    ups.package_config.spec_source_id = spec_source_id
    ups._fix_spec_source("fixed-source-archive.tar.gz")

    assert re.search(expected_line, u.joinpath("beer.spec").read_text())


def test_create_srpm(upstream_instance, tmp_path):
    u, ups = upstream_instance

    with pytest.raises(PackitSRPMException) as exc:
        ups.create_srpm()
    # Creating an SRPM failes b/c the source archive is not present.
    assert "tar.gz: No such file or directory" in str(exc.value)

    ups.create_archive()
    srpm = ups.create_srpm()

    assert srpm.exists()

    srpm_path = tmp_path.joinpath("custom.src.rpm")

    ups.prepare_upstream_for_srpm_creation()
    srpm = ups.create_srpm(srpm_path=srpm_path)
    r = re.compile(r"^- Development snapshot \(\w{8}\)$")
    with ups.specfile.sections() as sections:
        for line in sections.changelog:
            if r.match(line):
                break
        else:
            assert False, "Didn't find the correct line in the spec file."
    assert srpm.exists()
    build_srpm(srpm)


def test_create_srpm_git_desc_release(upstream_instance):
    u, ups = upstream_instance
    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()
    ups.prepare_upstream_for_srpm_creation()
    srpm = ups.create_srpm()
    assert srpm.exists()
    build_srpm(srpm)
    assert re.match(
        r".+beer-0.1.0-1\.\d{20}\.\w+\.\d\.g\w{7}\.(fc\d{2}|el\d).src.rpm$", str(srpm)
    )

    with ups.specfile.sections() as sections:
        assert "- More awesome changes (Packit Test Suite)" in sections.changelog


def test_github_app(upstream_instance, tmp_path):
    u, ups = upstream_instance

    fake_cert_path = tmp_path / "fake-cert.pem"
    fake_cert_path.write_text("hello!")

    user_config_file_path = tmp_path / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        f"authentication:\n"
        f"    github.com:\n"
        f"        github_app_private_key_path: {fake_cert_path}\n"
        f"        github_app_id: qwe\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path)
    )
    ups.config = Config.get_user_config()
    assert (
        GithubService(
            github_app_private_key_path=str(fake_cert_path), github_app_id="qwe"
        )
        in ups.config.services
    )


def test_get_last_tag(upstream_instance):
    u, ups = upstream_instance
    assert ups.get_last_tag() == "0.1.0"


@pytest.mark.parametrize(
    "template, expected_output",
    [
        pytest.param("{upstream_pkg_name}-{version}", "beerware-0.1.0", id="default"),
        pytest.param(
            "{version}-{upstream_pkg_name}", "0.1.0-beerware", id="ver-pkg_name"
        ),
    ],
)
def test_get_archive_root_dir(template, expected_output, upstream_instance):
    u, ups = upstream_instance
    flexmock(packit.upstream.tarfile).should_receive("is_tarfile").and_return(False)
    ups.package_config.archive_root_dir_template = template

    archive = ups.create_archive()
    archive_root_dir = Archive(ups, ups.get_version()).get_archive_root_dir(archive)

    assert archive_root_dir == expected_output


def test_create_archive_not_create_symlink(upstream_instance):
    """test archive creation when an archive is in root, but spec is in a subdir
    and create_symlink=False"""
    u, ups = upstream_instance

    archive_path = u.joinpath("beer.tar.gz")
    ups.package_config.actions[ActionName.create_archive] = [
        [
            "git",
            "archive",
            "--output",
            str(archive_path),
            "--prefix",
            f"{u.name}/",
            "HEAD",
        ],
        ["echo", str(archive_path)],
    ]

    packaging_dir = u / "packaging"
    packaging_dir.mkdir()
    spec_path = packaging_dir / "some.spec"
    spec_path.write_text("asd")
    ups._specfile_path = spec_path

    ups.create_archive(create_symlink=False)

    archives = list(packaging_dir.glob("*.tar.gz"))
    assert len(archives) == 1
    assert not archives[0].is_symlink()
