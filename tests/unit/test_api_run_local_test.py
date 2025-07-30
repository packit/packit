# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.exceptions import PackitCommandFailedError
from packit.utils import commands


@pytest.fixture
def mock_api():
    """Provide a PackitAPI instance with mocked dependencies."""
    # Create simple mock objects without instantiating real classes
    config = flexmock()
    package_config = flexmock()

    # Create the API instance with mock dependencies
    api = PackitAPI(config=config, package_config=package_config)

    # Return a flexmock of the API instance for easy mocking
    return flexmock(api)


def test_run_local_test_with_clean_before(mock_api):
    mock_api.should_receive("clean_tmt_artifacts").once()
    mock_api.should_receive("tmt_target_to_mock_root").with_args(
        "fedora:rawhide",
    ).and_return("fedora-rawhide-x86_64")
    mock_api.should_receive("_generate_rpms_for_tmt_test").and_return(
        [Path("/pkg.rpm")],
    )
    mock_api.should_receive("_build_tmt_cmd").and_return(["tmt", "run"])

    flexmock(commands).should_receive("run_command").and_return(
        flexmock(stderr="summary: 5 tests executed\nsummary: 5 tests passed"),
    )

    result = mock_api.run_local_test(target="fedora:rawhide", clean_before=True)
    assert result == "summary: 5 tests executed\nsummary: 5 tests passed"


def test_run_local_test_without_clean_before(mock_api):
    mock_api.should_receive("clean_tmt_artifacts").never()
    mock_api.should_receive("tmt_target_to_mock_root").and_return(
        "fedora-rawhide-x86_64",
    )
    mock_api.should_receive("_generate_rpms_for_tmt_test").and_return(
        [Path("/pkg.rpm")],
    )
    mock_api.should_receive("_build_tmt_cmd").and_return(["tmt", "run"])

    flexmock(commands).should_receive("run_command").and_return(
        flexmock(stderr="summary: 3 tests executed\nsummary: 2 tests passed"),
    )

    result = mock_api.run_local_test(target="fedora:rawhide", clean_before=False)
    assert result == "summary: 3 tests executed\nsummary: 2 tests passed"


def test_run_local_test_command_failure(mock_api):
    mock_api.should_receive("clean_tmt_artifacts").once()
    mock_api.should_receive("tmt_target_to_mock_root").and_return(
        "fedora-rawhide-x86_64",
    )
    mock_api.should_receive("_generate_rpms_for_tmt_test").and_return(
        [Path("/pkg.rpm")],
    )
    mock_api.should_receive("_build_tmt_cmd").and_return(["tmt", "run"])

    flexmock(commands).should_receive("run_command").and_raise(
        PackitCommandFailedError(
            "Command failed",
            stdout_output="",
            stderr_output="error output",
        ),
    )

    result = mock_api.run_local_test(target="fedora:rawhide")
    assert result is None
