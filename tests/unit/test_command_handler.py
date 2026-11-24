# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest
from flexmock import flexmock

from packit.command_handler import SandcastleCommandHandler
from packit.utils.commands import CommandResult

pytest.importorskip("sandcastle")


class SandcastleOutput:
    stdout = "version\n"
    stderr = "diagnostic\n"


def make_handler(config_mock):
    handler = SandcastleCommandHandler.__new__(SandcastleCommandHandler)
    handler.config = config_mock
    handler._working_dir = Path(config_mock.command_handler_work_dir)
    handler.local_project = None
    handler._sandcastle = flexmock(delete_pod=lambda: None)
    return handler


def test_sandcastle_command_handler_keeps_output_streams_separate(config_mock, caplog):
    handler = make_handler(config_mock)
    handler._sandcastle.should_receive("exec_with_output").with_args(
        command=["command"],
        env={"KEY": "value"},
        cwd=Path("relative"),
    ).and_return(SandcastleOutput())

    with caplog.at_level("INFO", logger="packit.command_handler"):
        result = handler.run_command(
            ["command"],
            env={"KEY": "value"},
            cwd="/mock_dir/sandcastle/relative",
            print_live=True,
        )

    assert result == CommandResult(True, "version\n", "diagnostic\n")
    assert "version" in caplog.text
    assert "diagnostic" in caplog.text


def test_sandcastle_command_handler_does_not_return_output_when_disabled(config_mock):
    handler = make_handler(config_mock)
    handler._sandcastle.should_receive("exec_with_output").and_return(
        SandcastleOutput(),
    )

    result = handler.run_command(["command"], return_output=False)

    assert result == CommandResult(True)


def test_sandcastle_command_handler_propagates_command_failure(config_mock):
    SandcastleCommandFailed = pytest.importorskip(
        "sandcastle.exceptions",
    ).SandcastleCommandFailed

    handler = make_handler(config_mock)
    failure = SandcastleCommandFailed(output="failure", reason="failed", rc=1)
    handler._sandcastle.should_receive("exec_with_output").and_raise(failure)

    with pytest.raises(SandcastleCommandFailed) as caught:
        handler.run_command(["command"])

    assert caught.value is failure


def test_sandcastle_command_handler_rejects_cwd_outside_workdir(config_mock):
    SandcastleCommandFailed = pytest.importorskip(
        "sandcastle.exceptions",
    ).SandcastleCommandFailed
    handler = make_handler(config_mock)

    with pytest.raises(SandcastleCommandFailed) as caught:
        handler.run_command(["command"], cwd="/outside")

    assert caught.value.rc == 1
    assert "is not within" in caught.value.reason
