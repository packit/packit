# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
from pathlib import Path

import pytest
from flexmock import flexmock

import packit
import packit.config.aliases
from packit.config import Config
from packit.config.aliases import Distro
from packit.distgit import DistGit
from packit.local_project import LocalProjectBuilder
from packit.sync import SyncFilesItem
from packit.upstream import GitUpstream
from tests.spellbook import CRONIE, get_test_config, initiate_git_repo


@pytest.fixture()
def mock_get_aliases():
    mock_aliases_module = flexmock(packit.config.aliases)
    mock_aliases_module.should_receive("get_aliases").and_return(
        {
            "fedora-all": [
                Distro("fedora-29", "f29"),
                Distro("fedora-30", "f30"),
                Distro("fedora-31", "f31"),
                Distro("fedora-32", "f32"),
                Distro("fedora-33", "f33"),
                Distro("fedora-rawhide", "rawhide"),
            ],
            "fedora-stable": [Distro("fedora-31", "f31"), Distro("fedora-32", "f32")],
            "fedora-branched": [Distro("fedora-33", "f33")],
            "fedora-development": [
                Distro("fedora-33", "f33"),
                Distro("fedora-rawhide", "rawhide"),
            ],
            "epel-all": [
                Distro("epel-6", "el6"),
                Distro("epel-7", "epel7"),
                Distro("epel-8", "epel8"),
                Distro("epel-9", "epel9"),
                Distro("epel-10.0", "epel10.0"),
                Distro("epel-10.1", "epel10"),
            ],
            "opensuse-leap-all": [
                "opensuse-leap-15.5",
                "opensuse-leap-15.4",
                "opensuse-leap-15.3",
            ],
            "opensuse-all": [
                "opensuse-tumbleweed",
                "opensuse-leap-15.5",
                "opensuse-leap-15.4",
                "opensuse-leap-15.3",
            ],
        },
    )


@pytest.fixture
def package_config_mock():
    files_to_sync = [
        SyncFilesItem(src=["specfile path"], dest="new specfile path"),
        SyncFilesItem(src=["packit config path"], dest="new packit config path"),
    ]
    mock = flexmock(
        files_to_sync=[],
        upstream_package_name="test_package_name",
        downstream_package_name="test_package_name",
        upstream_tag_template="_",
        upstream_project_url="_",
        allowed_gpg_keys="_",
        upstream_ref="_",
        create_sync_note=True,
        create_pr=False,
        actions=[],
        patch_generation_ignore_paths=[],
        patch_generation_patch_id_digits=4,
        is_sub_package=False,
        pkg_tool=None,
        version_update_mask="",
        parse_time_macros={},
    )
    mock.should_receive("get_package_names_as_env").and_return({})
    mock.should_receive("get_all_files_to_sync").and_return(files_to_sync)

    # simulate ‹MultiplePackages›
    mock._first_package = "default"
    mock.packages = {"default": mock}

    return mock


@pytest.fixture
def config_mock():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._github_token = "test"
    conf.fas_user = "packit"
    conf.command_handler_work_dir = "/mock_dir/sandcastle"
    return conf


@pytest.fixture
def git_project_mock():
    return (
        flexmock(upstream_project_url="dummy_url")
        .should_receive("get_release")
        .and_return(flexmock(url="url"))
        .mock()
    )


@pytest.fixture
def git_repo_mock():
    return flexmock(
        git=flexmock(
            checkout=lambda *_: None,
            reset=lambda *_: None,
            clean=lambda *_, **__: None,
            fetch=lambda *_: None,
            execute=lambda *_: None,
            rebase=lambda *_, **__: None,
        ),
        remote=lambda *_: flexmock(refs=[flexmock(remote_head="")]),
        branches=[],
        create_head=lambda *_, **__: None,
        head=flexmock(
            reset=lambda *_, **__: None,
            commit=flexmock(hexsha="", summary=""),
        ),
        untracked_files=[],
    )


@pytest.fixture
def local_project_mock(git_project_mock, git_repo_mock):
    flexmock(Path).should_receive("write_text")
    return flexmock(
        git_project=git_project_mock,
        working_dir=Path("/mock_dir/sandcastle/local-project"),
        ref="mock_ref",
        git_repo=git_repo_mock,
        checkout_release=lambda *_: None,
        commit_hexsha="_",
        repo_name="package",
        git_url="some-url",
    )


@pytest.fixture
def upstream_mock(local_project_mock, package_config_mock):
    upstream = GitUpstream(
        config=get_test_config(),
        package_config=package_config_mock,
        local_project=LocalProjectBuilder().build(
            working_dir="test",
            git_url="my-git-url",
        ),
    )
    flexmock(upstream)
    upstream.should_receive("local_project").and_return(local_project_mock)
    upstream.should_receive("absolute_specfile_path").and_return("_spec_file_path")
    upstream.should_receive("absolute_specfile_dir").and_return("_spec_file_dir")
    upstream.should_receive("is_dirty").and_return(False)
    upstream.should_receive("create_patches")

    return upstream


@pytest.fixture
def distgit_mock(local_project_mock, config_mock, package_config_mock):
    local_project = copy.copy(local_project_mock)
    local_project.working_dir = Path("/mock_dir/sandcastle/dist-git")
    distgit = DistGit(
        config=config_mock,
        package_config=package_config_mock,
        local_project=local_project,
    )
    flexmock(distgit)
    distgit.should_receive("is_dirty").and_return(False)
    distgit.should_receive("downstream_config").and_return(package_config_mock)
    distgit.should_receive("create_branch")
    distgit.should_receive("update_branch")
    distgit.should_receive("switch_branch")
    distgit.should_receive("commit")
    distgit.should_receive("push")
    distgit.should_receive("absolute_specfile_dir").and_return(Path("/mock_path"))
    distgit.should_receive("existing_pr").and_return(None)
    return distgit


@pytest.fixture
def cronie(tmp_path: Path):
    """c8s dist-git repo with cronie"""
    remote_url = "https://git.centos.org/rpms/cronie"
    d = tmp_path / "cronie"
    initiate_git_repo(
        d,
        copy_from=CRONIE,
        push=False,
        remotes=[
            ("origin", remote_url),
        ],
        empty_commits_count=0,
        add_initial_content=False,
    )
    return d
