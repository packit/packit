# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.cli import utils
from packit.cli.builds.mock_build import mock as mock_build_command
from packit.config import PackageConfig
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
