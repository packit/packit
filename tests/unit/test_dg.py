# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import re

import pytest
from flexmock import flexmock
from specfile import Specfile

from packit.cli.utils import get_packit_api
from packit.config import CommonPackageConfig, Config, PackageConfig
from packit.constants import DISTGIT_HOSTNAME_CANDIDATES, EXISTING_BODHI_UPDATE_REGEX
from packit.distgit import DistGit
from packit.local_project import LocalProjectBuilder
from packit.pkgtool import PkgTool


@pytest.mark.parametrize(
    "target_branch, source_branch, prs, exists",
    [
        (
            "f31",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                ),
            ],
            True,
        ),
        (
            "f32",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                ),
            ],
            False,
        ),
        (
            "f31",
            "f31-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit-stg",
                    source_branch="f31-update",
                ),
            ],
            False,
        ),
        (
            "f31",
            "f32-update",
            [
                flexmock(
                    title="Update",
                    target_branch="f31",
                    source_branch="f31-update",
                    description="Upstream tag: 0.4.0\nUpstream commit: 6957453b",
                    author="packit",
                ),
            ],
            False,
        ),
    ],
)
def test_existing_pr(git_repo_mock, target_branch, source_branch, prs, exists):
    user_mock = flexmock().should_receive("get_username").and_return("packit").mock()
    local_project = LocalProjectBuilder().build(
        git_project=flexmock(service="something", get_pr_list=lambda: prs),
        git_repo=git_repo_mock,
        git_service=flexmock(user=user_mock),
    )
    distgit = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(packages={"package": CommonPackageConfig()}),
        ),
        local_project=local_project,
    )
    pr = distgit.existing_pr(target_branch, source_branch)
    if exists:
        assert pr is not None
    else:
        assert pr is None


# Test covers the regression from monorepo refactoring that affects sync-release
# on downstream, since it directly accessed the attribute on the dist-git config
# instead of accessing specific package, which can cause ambiguity…
def test_monorepo_regression():
    config = flexmock(fas_user="mf")

    # Construct the package config; DON'T MOCK TO ENSURE IT CAN BE REPRODUCED
    package_a = flexmock(allowed_gpg_keys=["0xDEADBEEF"])
    package_b = flexmock(allowed_gpg_keys=["0xDEADBEEF"])
    package_config = PackageConfig(
        {
            "a": package_a,
            "b": package_b,
        },
    )

    dg = DistGit(config, package_config)

    # Assume the config has been synced to dist-git, therefore is 1:1 to the
    # one passed to DistGit class
    dg._downstream_config = package_config

    assert dg.get_allowed_gpg_keys_from_downstream_config() == ["0xDEADBEEF"]


# Test covers regex used for silencing of Bodhi exceptions for existing updates
@pytest.mark.parametrize(
    "exception_message, matches",
    [
        (
            (
                '{"status": "error", "errors": ['
                '{"location": "body", "name": "builds", "description": '
                '"Cannot find any tags associated with build: packit-0.79.1-1.el9"},'
                '{"location": "body", "name": "builds", "description": "Cannot '
                'find release associated with build: packit-0.79.1-1.el9, tags: []"}]}'
            ),
            False,
        ),
        (
            (
                '{"status": "error", "errors": ['
                '{"location": "body", "name": "builds", '
                '"description": "Update for linux-system-roles-1.53.4-1.fc39 already exists"}]}'
            ),
            True,
        ),
    ],
)
def test_bodhi_regex(exception_message, matches):
    assert bool(re.match(EXISTING_BODHI_UPDATE_REGEX, exception_message)) == matches


@pytest.mark.parametrize(
    "changelog, bugs",
    [
        (
            "* Fri Sep 29 2023 Packit <hello@packit.dev> - 0.82.0-1"
            "- Resolves rhbz#2240355",
            ["2240355"],
        ),
        (
            "* Fri Sep 29 2023 Packit <hello@packit.dev> - 0.82.0-1"
            "- Resolves rhbz#2240355"
            "- Resolves rhbz#2340355",
            ["2240355", "2340355"],
        ),
        (
            "* Fri Sep 29 2023 Packit <hello@packit.dev> - 0.82.0-1"
            "- Update without associated bugs",
            [],
        ),
    ],
)
def test_get_bugzilla_ids_from_changelog(changelog, bugs):
    assert DistGit.get_bugzilla_ids_from_changelog(changelog) == bugs


# Regression test for constructing the hostname candidates from the possible dist-git instances
def test_hostname_candidates():
    assert {
        "src.stg.fedoraproject.org",
        "gitlab.com",
        "src.fedoraproject.org",
        "pkgs.fedoraproject.org",
        "pkgs.stg.fedoraproject.org",
    } == DISTGIT_HOSTNAME_CANDIDATES


@pytest.mark.parametrize(
    "spec_source_id, with_coffee, archive_names",
    [
        ("Source0", "0", ["source0.tar.gz", "source2.tar.gz"]),
        ("Source1", "0", ["source0.tar.gz", "source1.tar.gz", "source2.tar.gz"]),
        ("Source2", "0", ["source0.tar.gz", "source2.tar.gz"]),
        ("Source2", "1", ["source0.tar.gz", "source2-with-coffee.tar.gz"]),
    ],
)
def test_upstream_archive_names(spec_source_id, with_coffee, archive_names, tmp_path):
    specfile_content = (
        "Name: test\n"
        "Version: 1.2.3\n"
        "Release: 1\n"
        "Source0: https://example.com/source0.tar.gz\n"
        "Source1: source1.tar.gz\n"
        "%if 0%{?with_coffee}\n"
        "Source2: https://example.com/source2-with-coffee.tar.gz\n"
        "%else\n"
        "Source2: https://example.com/source2.tar.gz\n"
        "%endif\n"
        "License: MIT\n"
        "Summary: test\n"
        "%description\ntest\n"
    )
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(specfile_content)
    specfile = Specfile(
        spec_path,
        sourcedir=tmp_path,
        autosave=True,
        macros=[("with_coffee", with_coffee)],
    )
    dg = DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="test.spec",
                        spec_source_id=spec_source_id,
                    ),
                },
            ),
        ),
    )
    flexmock(dg).should_receive("specfile").and_return(specfile)
    assert dg.upstream_archive_names == archive_names


def test_pkg_tool_details():

    SPECFILE_CONFIG_YAML = """
    {
        "upstream_project_url": "https://github.com/packit/specfile",
        "upstream_package_name": "specfile",
        "downstream_package_name": "python-specfile",
        "packages": {
            "specfile-centos-integration-sig": {
                "specfile_path": "centos-integration-sig/python-specfile.spec",
                "pkg_tool": "centpkg-sig",
                "sig": "Integration/packit-cbs"
            },
            "specfile-epel8": {
                "specfile_path": "epel8/python-specfile.spec"
            }
        },
        "jobs": [
            {
                "job": "propose_downstream",
                "trigger": "release",
                "dist_git_branches": ["epel8"],
                "packages": ["specfile-epel8"]
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "dist_git_branches": ["c9-sig-integration"],
                "packages": ["specfile-centos-integration-sig"]
            }
        ]
    }
    """
    packages_config_dict = json.loads(SPECFILE_CONFIG_YAML)
    packages_config = PackageConfig.get_from_dict(packages_config_dict)
    for package in ["specfile-centos-integration-sig", "specfile-epel8"]:
        package_view = packages_config.get_package_config_views()[package]

        api = get_packit_api(
            config=Config(fas_user="maja", pkg_tool="fedpkg"),
            package_config=package_view,
            dist_git_path="",
            local_project=flexmock(git_repo=flexmock(remotes=[])),
            check_for_non_git_upstream=False,
        )

        if package == "specfile-centos-integration-sig":
            flexmock(PkgTool).should_receive("__init__").with_args(
                fas_username="maja",
                directory="/tmp",
                tool="centpkg-sig",
                sig="Integration/packit-cbs",
            )
            flexmock(PkgTool).should_receive("clone").and_return()
        if package == "specfile-epel8":
            flexmock(PkgTool).should_receive("__init__").with_args(
                fas_username="maja",
                directory="/tmp",
                tool="fedpkg",
                sig=None,
            )
            flexmock(PkgTool).should_receive("clone").and_return()

        api.dg.clone_package("/tmp")
