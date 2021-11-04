# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from pkg_resources import get_distribution

from packit.cli.build import build
from packit.cli.create_update import create_update
from packit.cli.packit_base import packit_base
from packit.cli.propose_downstream import propose_downstream
from tests.spellbook import call_packit


def test_base_help():
    result = call_packit(parameters=["--help"])
    assert result.exit_code == 0
    assert "Usage: packit [OPTIONS] COMMAND [ARGS]..." in result.output


def test_base_version():
    # This test requires packit on pythonpath
    result = call_packit(parameters=["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == get_distribution("packitos").version


@pytest.mark.parametrize("cmd_function", [propose_downstream, build, create_update])
def test_base_subcommand_direct(cmd_function):
    result = call_packit(cmd_function, parameters=["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize("subcommand", ["propose-downstream", "build", "create-update"])
def test_base_subcommand_help(subcommand):
    result = call_packit(packit_base, parameters=[subcommand, "--help"])
    assert result.exit_code == 0
    assert f"Usage: packit {subcommand} [OPTIONS]" in result.output
