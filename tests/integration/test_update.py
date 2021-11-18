# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock

from packit.actions import ActionName
from packit.api import PackitAPI, Config
from packit.config import parse_loaded_config
from packit.local_project import LocalProject
from packit.specfile import Specfile
from tests.integration.conftest import mock_spec_download_remote_s
from tests.spellbook import TARBALL_NAME


@pytest.fixture()
def github_release_webhook():
    return {
        "repository": {
            "full_name": "brewery/beer",
            "owner": {"login": "brewery"},
            "name": "beer",
            "html_url": "https://github.com/brewery/beer",
        },
        "release": {
            "body": "Changelog content will be here",
            "tag_name": "0.1.0",
            "created_at": "2019-02-28T18:48:27Z",
            "published_at": "2019-02-28T18:51:10Z",
            "draft": False,
            "prerelease": False,
            "name": "Beer 0.1.0 is gooooood",
        },
        "action": "published",
    }


def test_basic_local_update(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    api.sync_release(dist_git_branch="main", version="0.1.0")

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.get_version() == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    changelog = "\n".join(spec.spec_content.section("%changelog"))
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_local_update_generated_spec(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    """Check that specfile can be generated on clone."""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    # Simulate generation by moving the spec to a different location
    current_spec_location = u / "beer.spec"
    new_spec_location = u / "tmp.spec"
    shutil.move(current_spec_location, new_spec_location)
    api.up.package_config.actions = {
        ActionName.post_upstream_clone: [
            f"mv {new_spec_location} {current_spec_location}"
        ]
    }
    api.sync_release(dist_git_branch="main")

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.get_version() == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    changelog = "\n".join(spec.spec_content.section("%changelog"))
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_reset_after_exception(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    """check whether the distgit repo is not dirty after exception is raised"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(api).should_receive("_handle_sources").and_raise(Exception)
    with pytest.raises(Exception):
        api.sync_release("main", "0.1.0")

    assert not api.dg.is_dirty()


def test_basic_local_update_copy_upstream_release_description(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git,
    set copy_upstream_release_description in package config to True"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    release = flexmock(body="Some description of the upstream release")
    api.up.local_project.git_project = flexmock(get_release=lambda name: release)
    api.package_config.copy_upstream_release_description = True
    api.sync_release(dist_git_branch="main", version="0.1.0")

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.get_version() == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    changelog = "\n".join(spec.spec_content.section("%changelog"))

    assert (
        """- 0.1.0-1
Some description of the upstream release
"""
        in changelog
    )

    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_using_distgit(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)

    api.sync_release(dist_git_branch="main", version="0.1.0")

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.get_version() == "0.1.0"

    package_section = spec.spec_content.section("%package")

    assert package_section[2] == "# some change"
    assert package_section[4] == "Name:           beer"
    assert package_section[5] == "Version:        0.1.0"
    assert package_section[6] == "Release:        1%{?dist}"
    assert package_section[7] == "Summary:        A tool to make you happy"

    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    changelog = "\n".join(spec.spec_content.section("%changelog"))
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_direct_push(
    cwd_upstream, api_instance, distgit_and_remote, mock_remote_functionality_upstream
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    _, distgit_remote = distgit_and_remote
    mock_spec_download_remote_s(d)

    api.sync_release(dist_git_branch="main", version="0.1.0", create_pr=False)

    remote_dir_clone = Path(f"{distgit_remote}-clone")
    subprocess.check_call(
        ["git", "clone", distgit_remote, str(remote_dir_clone)],
        cwd=str(remote_dir_clone.parent),
    )

    spec = Specfile(remote_dir_clone / "beer.spec")
    assert spec.get_version() == "0.1.0"
    assert (remote_dir_clone / "README.packit").is_file()


def test_basic_local_update_direct_push_no_dg_spec(
    cwd_upstream, api_instance, distgit_and_remote, mock_remote_functionality_upstream
):
    u, d, api = api_instance
    d.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(d),
    )
    _, distgit_remote = distgit_and_remote
    mock_spec_download_remote_s(d)

    api.sync_release(dist_git_branch="main", version="0.1.0", create_pr=False)

    remote_dir_clone = Path(f"{distgit_remote}-clone")
    subprocess.check_call(
        ["git", "clone", distgit_remote, str(remote_dir_clone)],
        cwd=str(remote_dir_clone.parent),
    )

    spec = Specfile(remote_dir_clone / "beer.spec")
    assert spec.get_version() == "0.1.0"
    assert (remote_dir_clone / "README.packit").is_file()


def test_basic_local_update_from_downstream(
    cwd_upstream, api_instance, mock_remote_functionality_upstream
):
    flexmock(LocalProject, _parse_namespace_from_git_url=lambda: None)
    u, d, api = api_instance

    api.sync_from_downstream("main", "main", True)

    new_upstream = api.up.local_project.working_dir
    assert (new_upstream / "beer.spec").is_file()
    spec = Specfile(new_upstream / "beer.spec")
    assert spec.get_version() == "0.0.0"


def test_local_update_with_specified_tag_template():
    c = Config()
    pc = parse_loaded_config(
        {
            "specfile_path": "beer.spec",
            "synced_files": ["beer.spec"],
            "upstream_package_name": "beerware",
            "downstream_package_name": "beer",
            "upstream_tag_template": "v{version}",
            "create_pr": False,
        }
    )
    api = PackitAPI(c, pc)

    assert (
        api.up.package_config.upstream_tag_template.format(version="0.1.0") == "v0.1.0"
    )
