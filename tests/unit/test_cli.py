import pytest
from click.testing import CliRunner

from packit.cli.packit_base import packit_base
from packit.cli.packit_base import version as cli_version
from packit.cli.update import update
from packit.cli.watch_upstream_release import watch_releases


def _call_packit(fnc=None, parameters=None, envs=None):
    fnc = fnc or packit_base
    runner = CliRunner()
    envs = envs or {}
    if not parameters:
        return runner.invoke(fnc, env=envs)
    else:
        return runner.invoke(fnc, parameters, env=envs)


def test_base_help():
    result = _call_packit(parameters=["--help"])
    assert result.exit_code == 0
    assert "Usage: packit [OPTIONS] COMMAND [ARGS]..." in result.output


def test_base_version_direct():
    result = _call_packit(cli_version)
    assert result.exit_code == 0


def test_base_version():
    result = _call_packit(parameters=["version"])
    assert result.exit_code == 0
    # TODO: figurate the correct version getter:
    # version = get_version(root="../..", relative_to=__file__)
    # name_ver = get_distribution(__name__).version
    # packit_ver = get_distribution("packit").version
    # packitos_ver = get_distribution("packitos").version
    # assert version in result.output


@pytest.mark.parametrize("cmd_function", [update, watch_releases])
def test_base_subcommand_direct(cmd_function):
    result = _call_packit(cmd_function, parameters=["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize("subcommand", ["propose-update", "watch-releases"])
def test_base_subcommand_help(subcommand):
    result = _call_packit(packit_base, parameters=[subcommand, "--help"])
    assert result.exit_code == 0
    assert f"Usage: packit {subcommand} [OPTIONS]" in result.output
