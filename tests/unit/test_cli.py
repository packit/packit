import pytest

from packit.cli.build import build
from packit.cli.create_update import create_update
from packit.cli.packit_base import packit_base
from packit.cli.packit_base import version as cli_version
from packit.cli.update import update
from packit.cli.watch_upstream_release import watch_releases
from tests.spellbook import call_packit


def test_base_help():
    result = call_packit(parameters=["--help"])
    assert result.exit_code == 0
    assert "Usage: packit [OPTIONS] COMMAND [ARGS]..." in result.output


def test_base_version_direct():
    # This test requires packit on pythonpath
    result = call_packit(cli_version)
    assert result.exit_code == 0


def test_base_version():
    # This test requires packit on pythonpath
    result = call_packit(parameters=["version"])
    assert result.exit_code == 0
    # TODO: figure out the correct version getter:
    # version = get_version(root="../..", relative_to=__file__)
    # name_ver = get_distribution(__name__).version
    # packit_ver = get_distribution("packit").version
    # packitos_ver = get_distribution("packitos").version
    # assert version in result.output


@pytest.mark.parametrize("cmd_function", [update, watch_releases, build, create_update])
def test_base_subcommand_direct(cmd_function):
    result = call_packit(cmd_function, parameters=["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "subcommand", ["propose-update", "watch-releases", "build", "create-update"]
)
def test_base_subcommand_help(subcommand):
    result = call_packit(packit_base, parameters=[subcommand, "--help"])
    assert result.exit_code == 0
    assert f"Usage: packit {subcommand} [OPTIONS]" in result.output
