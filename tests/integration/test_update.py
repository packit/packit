# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock
from ogr.abstract import PullRequest
from specfile import Specfile

from packit.actions import ActionName
from packit.api import Config, PackitAPI
from packit.config import parse_loaded_config
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.upstream import GitUpstream
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
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(Specfile).should_call("reload").at_least().once()

    api.sync_release(dist_git_branch="main", versions=["0.1.0"])

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_fast_forward_merge_local_update(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream_fast_forward_merge_branches,
):
    _, d, api = api_instance
    _, _ = mock_remote_functionality_upstream_fast_forward_merge_branches
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(Specfile).should_call("reload").at_least().once()
    flexmock(api.dg).should_call("create_pull").with_args(
        str,
        str,
        source_branch="main-update",
        target_branch="main",
    ).once()
    flexmock(api.dg).should_call("create_pull").with_args(
        str,
        str,
        source_branch="main-update",
        target_branch="f30",
    ).once()

    _, additional_prs = api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        fast_forward_merge_branches={"f30"},
    )
    assert list(additional_prs.keys()) == ["f30"]
    assert isinstance(additional_prs["f30"], PullRequest)

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_no_upload_to_lookaside(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(Specfile).should_call("reload").at_least().once()
    flexmock(DistGit).should_call("upload_to_lookaside_cache").with_args(
        archives=[d / "beerware-0.1.0.tar.gz"],
        pkg_tool="",
        offline=True,
    ).once()

    api.package_config.upload_sources = False
    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_missing_downstream_specfile(
    cwd_upstream,
    api_instance,
    distgit_and_remote,
    mock_remote_functionality_upstream,
    caplog,
):
    # log specfile debug messages
    caplog.set_level(logging.DEBUG)

    u, d, api = api_instance
    # remove the downstream specfile
    d.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(d),
    )
    subprocess.check_call(["git", "push", "-u", "origin", "main:main"], cwd=str(d))
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog

    with pytest.raises(FileNotFoundError):
        api.sync_release(
            dist_git_branch="main",
            versions=["0.1.0"],
            use_downstream_specfile=True,
        )


def test_basic_local_update_use_downstream_specfile(
    cwd_upstream,
    api_instance,
    distgit_and_remote,
    mock_remote_functionality_upstream,
    caplog,
):
    # log specfile debug messages
    caplog.set_level(logging.DEBUG)

    u, d, api = api_instance
    # remove the upstream specfile and push the tag that will be checked out
    u.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(u),
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"])
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        use_downstream_specfile=True,
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog

    # do this second time to see whether the specfile is updated correctly
    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        use_downstream_specfile=True,
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog

    assert changelog.count("0.1.0-1") == 1


def test_basic_local_update_use_downstream_specfile_non_git_upstream(
    cwd_upstream,
    api_instance,
    distgit_and_remote,
    mock_remote_functionality_upstream,
    caplog,
):
    # log specfile debug messages
    caplog.set_level(logging.DEBUG)

    u, d, api = api_instance
    api.non_git_upstream = True
    api._up = None

    # remove the upstream specfile and push the tag that will be checked out
    u.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(u),
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"])
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(api.up).should_receive("sync_files")

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        use_downstream_specfile=True,
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog

    # do this second time to see whether the specfile is updated correctly
    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        use_downstream_specfile=True,
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog

    assert changelog.count("0.1.0-1") == 1


def test_basic_local_update_with_multiple_sources(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d, files_to_create=["the_source.tar.gz"])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    for git_path in [u, d]:
        with Specfile(git_path / "beer.spec", autosave=True).sources() as sources:
            sources.append("https://the.second.source/the_source.tar.gz")
        subprocess.check_call(["git", "add", "beer.spec"], cwd=git_path)
        subprocess.check_call(
            ["git", "commit", "-m", "Added new source to specfile"],
            cwd=git_path,
        )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"], cwd=u)

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / "the_source.tar.gz"
    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source, dist_git_second_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert dist_git_second_source.is_file()

    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    with spec.sources() as sources:
        newly_added_source = sources[1]
        assert (
            newly_added_source.expanded_location
            == "https://the.second.source/the_source.tar.gz"
        )
        assert newly_added_source.filename == "the_source.tar.gz"
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_with_adding_second_source(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d, files_to_create=["the_source.tar.gz"])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    with Specfile(u / "beer.spec", autosave=True).sources() as sources:
        sources.append("https://the.second.source/the_source.tar.gz")
    subprocess.check_call(["git", "add", "beer.spec"], cwd=u)
    subprocess.check_call(
        ["git", "commit", "-m", "Added new source to specfile"],
        cwd=u,
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"], cwd=u)

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / "the_source.tar.gz"
    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source, dist_git_second_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert dist_git_second_source.is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    with spec.sources() as sources:
        newly_added_source = sources[1]
        assert (
            newly_added_source.expanded_location
            == "https://the.second.source/the_source.tar.gz"
        )
        assert newly_added_source.filename == "the_source.tar.gz"
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_with_adding_second_source_and_third_source_tracked_by_git(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    # add git-tracked key.asc
    subprocess.check_call(["touch", "key.asc"], cwd=d)
    subprocess.check_call(["git", "add", "key.asc"], cwd=d)
    subprocess.check_call(["git", "commit", "-m", "Added key.asc"], cwd=d)
    subprocess.check_call(["git", "fetch", "origin"], cwd=d)
    subprocess.check_call(["git", "push", "--tags", "-u", "origin", "main:main"], cwd=d)
    mock_spec_download_remote_s(d, files_to_create=[f"{TARBALL_NAME}.asc", "key.asc"])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    with Specfile(u / "beer.spec", autosave=True).sources() as sources:
        sources.append(f"https://upstream.net/{TARBALL_NAME}.asc")
        sources.append("https://upstream.net/key.asc")
    subprocess.check_call(["git", "add", "beer.spec"], cwd=u)
    subprocess.check_call(
        ["git", "commit", "-m", "Added new sources to specfile"],
        cwd=u,
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"], cwd=u)

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / f"{TARBALL_NAME}.asc"
    dist_git_third_source = d / "key.asc"

    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source, dist_git_second_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert dist_git_second_source.is_file()
    assert dist_git_third_source.is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_with_adding_second_local_source(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d, files_to_create=["the_source.tar.gz"])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    with Specfile(u / "beer.spec", autosave=True).sources() as sources:
        sources.append("the_source.tar.gz")
    subprocess.check_call(["git", "add", "beer.spec"], cwd=u)
    subprocess.check_call(
        ["git", "commit", "-m", "Added new source to specfile"],
        cwd=u,
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"], cwd=u)

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / "the_source.tar.gz"
    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source, dist_git_second_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert dist_git_second_source.is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    with spec.sources() as sources:
        newly_added_source = sources[1]
        assert newly_added_source.expanded_location == "the_source.tar.gz"
        assert newly_added_source.filename == "the_source.tar.gz"
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_with_adding_second_local_source_tracked_by_git(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d, files_to_create=["the_source.tar.gz"])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    with Specfile(u / "beer.spec", autosave=True).sources() as sources:
        sources.append("README")
    subprocess.check_call(["git", "add", "beer.spec"], cwd=u)
    subprocess.check_call(
        ["git", "commit", "-m", "Added new source to specfile"],
        cwd=u,
    )
    subprocess.check_call(["git", "tag", "0.1.0", "-f"], cwd=u)

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / "README"

    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert dist_git_second_source.is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_with_removing_second_source(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d, files_to_create=[])
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    with Specfile(d / "beer.spec", autosave=True).sources() as sources:
        sources.append("https://the.second.source/the_source.tar.gz")
    subprocess.check_call(["git", "add", "beer.spec"], cwd=d)
    subprocess.check_call(
        ["git", "commit", "-m", "Added new source to specfile"],
        cwd=d,
    )
    api.dg.specfile.reload()

    dist_git_first_source = d / TARBALL_NAME
    dist_git_second_source = d / "the_source.tar.gz"
    flexmock(api.dg).should_call("upload_to_lookaside_cache").with_args(
        archives=[dist_git_first_source],
        pkg_tool="",
        offline=False,
    )

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert dist_git_first_source.is_file()
    assert not dist_git_second_source.is_file()

    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    with spec.sources() as sources:
        assert len(sources) == 1  # The second source should be removed
    assert spec.sources()
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_local_update_generated_spec(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """Check that specfile can be generated on clone."""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(GitUpstream).should_receive("get_latest_released_version").and_return(
        "0.1.0",
    )

    # Simulate generation by moving the spec to a different location
    # We are checking two things:
    # * spec-file is not used before the post-upstream-clone
    # * the version is get from the release state
    current_spec_location = u / "beer.spec"
    new_spec_location = u / ".." / "tmp.spec"
    shutil.move(current_spec_location, new_spec_location)
    subprocess.check_call(["git", "add", "beer.spec"], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "Spec removed from upstream"], cwd=u)
    api.up.package_config.actions = {
        ActionName.post_upstream_clone: [
            f"mv {new_spec_location} {current_spec_location}",
        ],
    }

    api.sync_release(dist_git_branch="main")

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_reset_after_exception(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
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
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git,
    set copy_upstream_release_description in package config to True"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    release = flexmock(body="Some description of the upstream release", url="some-url")
    api.up.local_project.git_project = flexmock(
        get_release=lambda name, tag_name: release,
    )
    api.package_config.copy_upstream_release_description = True
    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)

    assert (
        """- 0.1.0-1
Some description of the upstream release
"""
        in changelog
    )

    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_using_distgit(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    mock_spec_download_remote_s(d)

    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
    )

    assert (d / TARBALL_NAME).is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"

    with spec.sections() as sections:
        package_section = sections.package

    assert package_section[2] == "# some change"
    assert package_section[4] == "Name:           beer"
    assert package_section[5] == "Version:        0.1.0"
    assert package_section[6] == "Release:        1%{?dist}"
    assert package_section[7] == "Summary:        A tool to make you happy"

    assert (d / "README.packit").is_file()
    # assert that we have changelog entries for both versions
    with spec.sections() as sections:
        changelog = "\n".join(sections.changelog)
    assert "0.0.0" in changelog
    assert "0.1.0" in changelog


def test_basic_local_update_direct_push(
    cwd_upstream,
    api_instance,
    distgit_and_remote,
    mock_remote_functionality_upstream,
):
    """basic propose-downstream test: mock remote API, use local upstream and dist-git"""
    u, d, api = api_instance
    _, distgit_remote = distgit_and_remote
    mock_spec_download_remote_s(d)

    api.sync_release(dist_git_branch="main", versions=["0.1.0"], create_pr=False)

    remote_dir_clone = Path(f"{distgit_remote}-clone")
    subprocess.check_call(
        ["git", "clone", distgit_remote, str(remote_dir_clone)],
        cwd=str(remote_dir_clone.parent),
    )

    spec = Specfile(remote_dir_clone / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (remote_dir_clone / "README.packit").is_file()


def test_update_downstream_changelog_even_if_has_autochangelog(
    cwd_upstream,
    api_instance,
    distgit_with_autochangelog_and_remote,
    mock_remote_functionality_downstream_autochangelog,
):
    """Check that a new entry is added to the %changelog section of the the spec-file in dist-git,
    when sync_changelog is set, even if the spec-file in dist-git uses %autochangelog"""
    u, d, api = api_instance
    _, distgit_remote = distgit_with_autochangelog_and_remote

    api.package_config.sync_changelog = True
    api.sync_release(
        dist_git_branch="main",
        versions=["0.1.0"],
        create_pr=False,
        add_new_sources=False,
    )

    assert api.dg.specfile.version == "0.1.0"
    with api.dg.specfile.sections() as sections:
        assert (
            "* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1"
            in sections.changelog
        )


def test_basic_local_update_direct_push_no_dg_spec(
    cwd_upstream,
    api_instance,
    distgit_and_remote,
    mock_remote_functionality_upstream,
):
    u, d, api = api_instance
    d.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(d),
    )
    _, distgit_remote = distgit_and_remote
    mock_spec_download_remote_s(d)

    api.sync_release(dist_git_branch="main", versions=["0.1.0"], create_pr=False)

    remote_dir_clone = Path(f"{distgit_remote}-clone")
    subprocess.check_call(
        ["git", "clone", distgit_remote, str(remote_dir_clone)],
        cwd=str(remote_dir_clone.parent),
    )

    spec = Specfile(remote_dir_clone / "beer.spec")
    assert spec.expanded_version == "0.1.0"
    assert (remote_dir_clone / "README.packit").is_file()


def test_basic_local_update_from_downstream(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    flexmock(LocalProject, _parse_namespace_from_git_url=lambda: None)
    u, d, api = api_instance

    api.sync_from_downstream("main", "main", True)

    new_upstream = api.up.local_project.working_dir
    assert (new_upstream / "beer.spec").is_file()
    spec = Specfile(new_upstream / "beer.spec")
    assert spec.expanded_version == "0.0.0"


def test_local_update_with_specified_tag_template():
    c = Config()
    pc = parse_loaded_config(
        {
            "specfile_path": "beer.spec",
            "files_to_sync": ["beer.spec"],
            "upstream_package_name": "beerware",
            "downstream_package_name": "beer",
            "upstream_tag_template": "v{version}",
            "create_pr": False,
        },
    )
    api = PackitAPI(c, pc)

    assert (
        api.up.package_config.upstream_tag_template.format(version="0.1.0") == "v0.1.0"
    )


def test_basic_local_update_post_modifications_action(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    u, d, api = api_instance
    mock_spec_download_remote_s(d)
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(Specfile).should_call("reload").at_least().once()

    # just to make PACKIT_DOWNSTREAM_REPO available
    api.dg._local_project = flexmock()

    api.up.package_config.actions = {
        ActionName.post_modifications: [
            f"bash -c 'cd $PACKIT_DOWNSTREAM_REPO && md5sum {TARBALL_NAME} > source.hash'",
        ],
    }
    api.sync_release(dist_git_branch="main", versions=["0.1.0"])

    assert (d / TARBALL_NAME).is_file()
    assert (d / "source.hash").is_file()
    spec = Specfile(d / "beer.spec")
    assert spec.expanded_version == "0.1.0"
