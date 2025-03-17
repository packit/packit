# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functional tests the validate-config command
"""

from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from packit.cli.validate_config import validate_config
from packit.utils.commands import cwd
from tests.functional.spellbook import call_real_packit_and_return_exit_code


def test_srpm_command_for_path(upstream_or_distgit_path, tmp_path):
    with cwd(tmp_path):
        call_real_packit_and_return_exit_code(
            parameters=["--debug", "validate-config", str(upstream_or_distgit_path)],
        )


import logging
from pathlib import Path

import pytest


@pytest.fixture
def dummy_local_project(tmp_path):
    dummy = MagicMock()
    dummy.working_dir = str(tmp_path)
    return dummy


def test_valid_config_option(tmp_path, dummy_local_project, caplog):
    """
    Test that the -c/--config option works correctly when a valid configuration file is provided.
    """
    config = Path(dummy_local_project.working_dir) / ".packit.yaml"
    config.write_text(
        "specfile_path: valid.spec\n"
        "upstream_project_url: https://example.com/repo\n"
        "downstream_package_name: valid-package\n",
    )
    runner = CliRunner()
    with (
        patch(
            "packit.cli.validate_config.LocalProjectParameter.convert",
            return_value=dummy_local_project,
        ),
        patch("packit.cli.validate_config.load_packit_yaml") as mock_load,
        patch(
            "packit.cli.validate_config.PackageConfigValidator",
        ) as mock_validator_cls,
    ):
        mock_load.return_value = {
            "specfile_path": "valid.spec",
            "upstream_project_url": "https://example.com/repo",
            "downstream_package_name": "valid-package",
        }
        instance = mock_validator_cls.return_value
        instance.validate.return_value = "Configuration is valid"
        with caplog.at_level(logging.INFO):
            result = runner.invoke(
                validate_config,
                [dummy_local_project.working_dir, "--config", str(config)],
            )
        assert result.exit_code == 0
        assert f"Validating config file: {config}" in caplog.text
        assert "Configuration is valid" in caplog.text


def test_missing_config_file(tmp_path, dummy_local_project, caplog):
    """
    Test that if no configuration file is provided or found, an appropriate error is logged.
    """
    missing_config = Path(dummy_local_project.working_dir) / "nonexistent.yaml"
    runner = CliRunner()
    with (
        patch(
            "packit.cli.validate_config.LocalProjectParameter.convert",
            return_value=dummy_local_project,
        ),
        patch(
            "packit.cli.validate_config.find_packit_yaml", return_value=missing_config,
        ),
    ):
        with caplog.at_level(logging.ERROR):
            result = runner.invoke(validate_config, [dummy_local_project.working_dir])
    assert "Configuration file not found:" in caplog.text
    assert str(missing_config) in caplog.text


def test_yaml_syntax_error(tmp_path, dummy_local_project, caplog):
    """
    Test that a YAML syntax error in the configuration file is handled correctly.
    """
    config = Path(dummy_local_project.working_dir) / ".packit.yaml"
    config.write_text("invalid: [yaml")
    runner = CliRunner()
    with (
        patch(
            "packit.cli.validate_config.LocalProjectParameter.convert",
            return_value=dummy_local_project,
        ),
        patch("packit.cli.validate_config.load_packit_yaml") as mock_load,
    ):
        mock_load.side_effect = yaml.YAMLError("Simulated YAML syntax error")
        with caplog.at_level(logging.ERROR):
            result = runner.invoke(
                validate_config,
                [dummy_local_project.working_dir, "--config", str(config)],
            )
    assert "Failed to parse YAML file" in caplog.text
