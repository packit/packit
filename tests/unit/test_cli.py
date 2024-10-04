# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from importlib.metadata import version

import pytest
from flexmock import flexmock

from packit.cli import propose_downstream as propose_downstream_module
from packit.cli import utils
from packit.cli.build import build
from packit.cli.create_update import create_update
from packit.cli.packit_base import packit_base
from packit.cli.propose_downstream import propose_downstream
from packit.config import Config, PackageConfig
from packit.local_project import LocalProject
from tests.spellbook import call_packit


def test_base_help():
    result = call_packit(parameters=["--help"])
    assert result.exit_code == 0
    assert "Usage: packit [OPTIONS] COMMAND [ARGS]..." in result.output


def test_base_version():
    # This test requires packit on pythonpath
    result = call_packit(parameters=["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == version("packitos")


@pytest.mark.parametrize("cmd_function", [propose_downstream, build, create_update])
def test_base_subcommand_direct(cmd_function):
    result = call_packit(cmd_function, parameters=["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize("subcommand", ["propose-downstream", "build", "create-update"])
def test_base_subcommand_help(subcommand):
    result = call_packit(packit_base, parameters=[subcommand, "--help"])
    assert result.exit_code == 0
    assert f"Usage: packit {subcommand} [OPTIONS]" in result.output


def test_propose_downstream_command():
    flexmock(utils).should_receive("get_local_package_config").and_return(
        flexmock().should_receive("get_package_config_views").and_return({}).mock(),
    )
    flexmock(propose_downstream_module).should_receive("sync_release").with_args(
        config=Config,
        dist_git_path=None,
        dist_git_branch=None,
        force_new_sources=False,
        pr=None,
        path_or_url=LocalProject,
        version=None,
        force=False,
        local_content=False,
        upstream_ref=None,
        use_downstream_specfile=False,
        package_config=PackageConfig,
        resolve_bug=None,
        sync_acls=False,
    ).and_return()
    result = call_packit(packit_base, parameters=["propose-downstream", "."])
    assert result.exit_code == 0


def test_pull_from_upstream_command():
    flexmock(utils).should_receive("get_local_package_config").and_return(
        flexmock().should_receive("get_package_config_views").and_return({}).mock(),
    )
    flexmock(propose_downstream_module).should_receive("sync_release").with_args(
        config=Config,
        dist_git_path=None,
        dist_git_branch=None,
        force_new_sources=False,
        pr=None,
        path_or_url=LocalProject,
        version=None,
        force=False,
        local_content=False,
        upstream_ref=None,
        use_downstream_specfile=True,
        package_config=PackageConfig,
        resolve_bug=None,
        sync_acls=False,
    ).and_return()
    result = call_packit(packit_base, parameters=["pull-from-upstream", "."])
    assert result.exit_code == 0
