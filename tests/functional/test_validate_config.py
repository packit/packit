# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functional tests the validate-config command
"""

import logging
from unittest.mock import patch

import pytest
import yaml
from flexmock import flexmock

from packit.api import PackitAPI
from packit.utils.commands import cwd
from tests.functional.spellbook import call_real_packit_and_return_exit_code


def test_srpm_command_for_path(upstream_or_distgit_path, tmp_path):
    with cwd(tmp_path):
        call_real_packit_and_return_exit_code(
            parameters=["--debug", "validate-config", str(upstream_or_distgit_path)],
        )


@pytest.fixture
def dummy_local_project(tmp_path):
    """Fixture that creates a mock local project with a working directory."""
    return flexmock(working_dir=tmp_path)


def test_valid_config_option(tmp_path, dummy_local_project, caplog):
    """
    Test that validate_package_config correctly validates a proper configuration file.
    """
    config_path = tmp_path / ".packit.yaml"
    config_path.write_text(
        "specfile_path: valid.spec\n"
        "upstream_project_url: https://example.com/repo\n"
        "downstream_package_name: valid-package\n",
    )

    with (
        patch("packit.api.load_packit_yaml") as mock_load,
        patch("packit.api.PackageConfigValidator") as mock_validator_cls,
        caplog.at_level(logging.INFO),
    ):
        mock_load.return_value = {
            "specfile_path": "valid.spec",
            "upstream_project_url": "https://example.com/repo",
            "downstream_package_name": "valid-package",
        }
        instance = mock_validator_cls.return_value
        instance.validate.return_value = "Configuration is valid"

        result = PackitAPI.validate_package_config(
            working_dir=dummy_local_project.working_dir,
            offline=False,
            config=str(config_path),
        )

    assert result == "Configuration is valid"
    assert f"Validating config file: {config_path}" in caplog.text


def test_missing_config_file(tmp_path, dummy_local_project, caplog):
    """
    Test that validate_package_config logs an error and returns None when no config file is found.
    """
    missing_config = tmp_path / "nonexistent.yaml"

    with (
        patch("packit.api.find_packit_yaml", return_value=missing_config),
        caplog.at_level(logging.ERROR),
    ):
        result = PackitAPI.validate_package_config(
            working_dir=dummy_local_project.working_dir,
            offline=False,
        )

    assert result is None
    assert f"Configuration file not found: {missing_config}" in caplog.text


def test_yaml_syntax_error(tmp_path, dummy_local_project, caplog):
    """
    Test that validate_package_config handles a YAML syntax error correctly.
    """
    config_path = tmp_path / ".packit.yaml"
    config_path.write_text("invalid: [yaml")

    with (
        patch("packit.api.load_packit_yaml") as mock_load,
        caplog.at_level(logging.ERROR),
    ):
        mock_load.side_effect = yaml.YAMLError("Simulated YAML syntax error")

        result = PackitAPI.validate_package_config(
            working_dir=dummy_local_project.working_dir,
            offline=False,
            config=str(config_path),
        )

    assert result is None
    assert "Failed to parse YAML file: Simulated YAML syntax error" in caplog.text


def test_default_config_discovery(tmp_path, dummy_local_project, caplog):
    """
    Test that validate_package_config finds and validates a default .packit.yaml file.
    """
    config_path = tmp_path / ".packit.yaml"
    config_path.write_text(
        "specfile_path: valid.spec\n"
        "upstream_project_url: https://example.com/repo\n"
        "downstream_package_name: valid-package\n",
    )

    with (
        patch("packit.api.find_packit_yaml", return_value=config_path),
        patch("packit.api.load_packit_yaml") as mock_load,
        patch("packit.api.PackageConfigValidator") as mock_validator_cls,
        caplog.at_level(logging.INFO),
    ):
        mock_load.return_value = {
            "specfile_path": "valid.spec",
            "upstream_project_url": "https://example.com/repo",
            "downstream_package_name": "valid-package",
        }
        instance = mock_validator_cls.return_value
        instance.validate.return_value = "Configuration is valid"

        result = PackitAPI.validate_package_config(
            working_dir=dummy_local_project.working_dir,
            offline=False,
            config=None,
        )

    assert result == "Configuration is valid"
    assert f"Validating config file: {config_path}" in caplog.text
