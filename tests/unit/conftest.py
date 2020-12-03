from pathlib import Path

import pytest
from flexmock import flexmock
from munch import munchify

import packit
from packit.config import Config
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import get_test_config


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
        response = {"releases": releases}
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
        create_pr=False,
        actions=[],
        patch_generation_ignore_paths=[],
    )
    mock.should_receive("current_version_command")
    mock.should_receive("get_all_files_to_sync.get_raw_files_to_sync").and_return([])
    return mock


@pytest.fixture
def config_mock():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._github_token = "test"
    return conf


@pytest.fixture
def git_project_mock():
    mock = flexmock(upstream_project_url="dummy_url")
    return mock


@pytest.fixture
def git_repo_mock():
    git_repo = flexmock(
        git=flexmock(checkout=lambda *_: None, reset=lambda *_: None),
        remote=lambda *_: flexmock(refs={"_": "_"}),
        branches=[],
        create_head=lambda *_, **__: None,
    )
    return git_repo


@pytest.fixture
def local_project_mock(git_project_mock, git_repo_mock):
    flexmock(Path).should_receive("write_text")
    mock = flexmock(
        git_project=git_project_mock,
        working_dir=Path("/mock_dir"),
        ref="mock_ref",
        git_repo=git_repo_mock,
        checkout_release=lambda *_: None,
        commit_hexsha="_",
    )
    return mock


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
    return distgit
