# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest
from flexmock import flexmock
from munch import munchify

import packit
from packit.config import Config
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import get_test_config, CRONIE, initiate_git_repo


@pytest.fixture
def bodhi_client_response():
    def response_factory(releases_list):
        releases = [
            {
                "name": name,
                "long_name": long_name,
                "id_prefix": id_prefix,
                "state": state,
            }
            for name, long_name, id_prefix, state in releases_list
        ]
        response = {"releases": releases, "page": 1, "pages": 1}
        return munchify(response)

    return response_factory


@pytest.fixture()
def mock_get_aliases():
    mock_aliases_module = flexmock(packit.config.aliases)
    mock_aliases_module.should_receive("get_aliases").and_return(
        {
            "fedora-all": ["fedora-31", "fedora-32", "fedora-33", "fedora-rawhide"],
            "fedora-stable": ["fedora-31", "fedora-32"],
            "fedora-development": ["fedora-33", "fedora-rawhide"],
            "epel-all": ["epel-6", "epel-7", "epel-8"],
        }
    )


@pytest.fixture
def package_config_mock():
    mock = flexmock(
        synced_files=None,
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
    )
    mock.should_receive("get_all_files_to_sync").and_return([])
    return mock


@pytest.fixture
def config_mock():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._github_token = "test"
    return conf


@pytest.fixture
def git_project_mock():
    return flexmock(upstream_project_url="dummy_url")


@pytest.fixture
def git_repo_mock():
    return flexmock(
        git=flexmock(checkout=lambda *_: None, reset=lambda *_: None),
        remote=lambda *_: flexmock(refs={"_": "_"}),
        branches=[],
        create_head=lambda *_, **__: None,
    )


@pytest.fixture
def local_project_mock(git_project_mock, git_repo_mock):
    flexmock(Path).should_receive("write_text")
    return flexmock(
        git_project=git_project_mock,
        working_dir=Path("/mock_dir"),
        ref="mock_ref",
        git_repo=git_repo_mock,
        checkout_release=lambda *_: None,
        commit_hexsha="_",
    )


@pytest.fixture
def upstream_mock(local_project_mock, package_config_mock):
    upstream = Upstream(
        config=get_test_config(),
        package_config=package_config_mock,
        local_project=LocalProject(working_dir="test"),
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
    distgit = DistGit(
        config=config_mock,
        package_config=package_config_mock,
        local_project=local_project_mock,
    )
    flexmock(distgit)
    distgit.should_receive("is_dirty").and_return(False)
    distgit.should_receive("downstream_config").and_return(package_config_mock)
    distgit.should_receive("create_branch")
    distgit.should_receive("update_branch")
    distgit.should_receive("checkout_branch")
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
