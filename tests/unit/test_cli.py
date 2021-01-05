# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
from pkg_resources import get_distribution

from packit.cli.build import build
from packit.cli.create_update import create_update
from packit.cli.packit_base import packit_base
from packit.cli.propose_downstream import downstream
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


@pytest.mark.parametrize("cmd_function", [downstream, build, create_update])
def test_base_subcommand_direct(cmd_function):
    result = call_packit(cmd_function, parameters=["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize("subcommand", ["propose-update", "build", "create-update"])
def test_base_subcommand_help(subcommand):
    result = call_packit(packit_base, parameters=[subcommand, "--help"])
    assert result.exit_code == 0
    assert f"Usage: packit {subcommand} [OPTIONS]" in result.output
