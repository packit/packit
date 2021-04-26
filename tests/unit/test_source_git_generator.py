# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from pathlib import Path

from flexmock import flexmock

from packit.config import Config
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.source_git import SourceGitGenerator, CentOS8DistGit
from packit.utils.repo import create_new_repo


def test_centos_conf(cronie, tmp_path: Path):
    """make sure the centos-specific configuration is correct"""
    source_git_path = tmp_path.joinpath("cronie-sg")
    # create src-git
    source_git_path.mkdir()
    create_new_repo(source_git_path, [])
    sgg = SourceGitGenerator(
        LocalProject(working_dir=source_git_path),
        Config(),
        dist_git_path=cronie,
        upstream_ref="cronie-1.5.2",
        centos_package="cronie",
    )

    dg = sgg.dist_git
    assert isinstance(dg, CentOS8DistGit)

    flexmock(
        DistGit,
        download_upstream_archive=lambda: cronie / "SOURCES" / "cronie-1.5.2.tar.gz",
    )
    assert sgg.primary_archive == cronie / "SOURCES" / "cronie-1.5.2.tar.gz"

    assert dg.absolute_source_dir == cronie / "SOURCES"
    assert dg.absolute_specfile_dir == cronie / "SPECS"
    assert dg.absolute_specfile_path == cronie / "SPECS" / "cronie.spec"
