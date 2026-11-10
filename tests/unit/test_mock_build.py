# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import grp
import logging
import os
from pathlib import Path

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.cli import utils
from packit.cli.builds.mock_build import mock as mock_build_command
from packit.config import PackageConfig
from packit.upstream import GitUpstream
from tests.spellbook import call_packit


@pytest.fixture
def mock_api():
    return flexmock(PackitAPI).should_receive("run_mock_build").mock()


@pytest.fixture
def mock_package_config():
    package_config_mock = flexmock(PackageConfig)
    flexmock(utils).should_receive("get_local_package_config").and_return(
        package_config_mock,
    )
    return package_config_mock


def test_build_in_mock_default_resultdir(mock_api, mock_package_config):
    flexmock(PackitAPI).should_receive("run_mock_build").with_args(
        root="default",
        srpm_path=None,
        resultdir=".",
    ).and_return(["test.rpm"])

    result = call_packit(mock_build_command, parameters=["build", "in-mock"])
    print(f"Exit Code: {result.exit_code}")


def test_build_in_mock_default_resultdir_flag(mock_api, mock_package_config):
    flexmock(PackitAPI).should_receive("run_mock_build").with_args(
        root="default",
        srpm_path=None,
        resultdir=None,
    ).and_return(["test.rpm"])

    result = call_packit(mock_build_command, ["in-mock", "--default-resultdir"])
    print(f"Exit Code: {result.exit_code}")
    print(f"Output: {result.output}")


def test_build_in_mock_custom_resultdir(mock_api, mock_package_config):
    custom_resultdir = "/custom/path"
    flexmock(PackitAPI).should_receive("run_mock_build").with_args(
        root="default",
        srpm_path=None,
        resultdir=custom_resultdir,
    ).and_return(["test.rpm"])

    result = call_packit(
        mock_build_command,
        ["in-mock", "--resultdir", custom_resultdir],
    )
    print(f"Exit Code: {result.exit_code}")
    print(f"Output: {result.output}")


@pytest.fixture
def api_for_mock_build(config_mock, package_config_mock, upstream_mock):
    api = PackitAPI(config=config_mock, package_config=package_config_mock)
    flexmock(api)
    api._up = upstream_mock
    return api


def mock_group_check(member):
    """Pretend the `mock` group has gid 1234 and the user is (not) in it."""
    flexmock(grp).should_receive("getgrnam").with_args("mock").and_return(
        flexmock(gr_gid=1234),
    )
    if member:
        flexmock(os).should_receive("getgroups").and_return([1234])
    else:
        flexmock(os).should_receive("getgroups").and_return([1000])
    flexmock(os).should_receive("getgid").and_return(1000)


def test_is_user_in_mock_group_member():
    mock_group_check(member=True)
    assert PackitAPI.is_user_in_mock_group() is True


def test_is_user_in_mock_group_member_via_primary_group():
    flexmock(grp).should_receive("getgrnam").with_args("mock").and_return(
        flexmock(gr_gid=1234),
    )
    flexmock(os).should_receive("getgroups").and_return([1000])
    flexmock(os).should_receive("getgid").and_return(1234)
    assert PackitAPI.is_user_in_mock_group() is True


def test_is_user_in_mock_group_not_member():
    mock_group_check(member=False)
    assert PackitAPI.is_user_in_mock_group() is False


def test_is_user_in_mock_group_no_mock_group():
    flexmock(grp).should_receive("getgrnam").with_args("mock").and_raise(KeyError)
    assert PackitAPI.is_user_in_mock_group() is True


def run_mock_build_with_mocked_command(api_for_mock_build, upstream_mock):
    """Run run_mock_build with the `mock` command itself mocked out."""
    command_handler = flexmock()
    command_handler.should_receive("run_command").with_args(
        ["mock", "--root", "default", "/tmp/test-1.0-1.src.rpm"],
        return_output=True,
    ).and_return(flexmock(stderr="mock output"))
    upstream_mock._command_handler = command_handler
    flexmock(GitUpstream).should_receive("_get_rpms_from_mock_output").with_args(
        "mock output",
    ).and_return(["/tmp/test-1.0-1.noarch.rpm"])
    return api_for_mock_build.run_mock_build(
        srpm_path=Path("/tmp/test-1.0-1.src.rpm"),
    )


def test_run_mock_build_warns_when_user_not_in_mock_group(
    api_for_mock_build,
    upstream_mock,
    caplog,
):
    flexmock(PackitAPI).should_receive("is_user_in_mock_group").and_return(False)

    with caplog.at_level(logging.WARNING, logger="packit.api"):
        result = run_mock_build_with_mocked_command(api_for_mock_build, upstream_mock)

    assert result == [Path("/tmp/test-1.0-1.noarch.rpm")]
    assert "You are not in the `mock` group" in caplog.text
    assert "rpm-software-management.github.io/mock/#setup" in caplog.text


def test_run_mock_build_no_warning_when_user_in_mock_group(
    api_for_mock_build,
    upstream_mock,
    caplog,
):
    flexmock(PackitAPI).should_receive("is_user_in_mock_group").and_return(True)

    with caplog.at_level(logging.WARNING, logger="packit.api"):
        result = run_mock_build_with_mocked_command(api_for_mock_build, upstream_mock)

    assert result == [Path("/tmp/test-1.0-1.noarch.rpm")]
    assert "not in the `mock` group" not in caplog.text
