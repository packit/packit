# Copyright (c) 2025, Your Name or Organization
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.config.package_config_validator import PackageConfigValidator
from packit.exceptions import PackitConfigException


def test_invalid_upstream_tag_template_type(tmp_path):
    config_dict = {
        "upstream_tag_template": 123,  # invalid type
        "specfile_path": "my_specfile.spec",  # Ensure specfile path is provided
    }
    validator = PackageConfigValidator(
        config_content=config_dict,
        config_file_path=tmp_path / "packit.yaml",
        project_path=tmp_path,
    )
    # Adjusted the expected error message to match the actual exception message
    with pytest.raises(PackitConfigException, match="Not a valid string"):
        validator.validate()


def test_invalid_upstream_tag_template_format(tmp_path):
    config_dict = {
        "upstream_tag_template": "{invalid",  # invalid format string
        "specfile_path": "my_specfile.spec",  # Ensure specfile path is provided
    }
    validator = PackageConfigValidator(
        config_content=config_dict,
        config_file_path=tmp_path / "packit.yaml",
        project_path=tmp_path,
    )
    # Adjusted the expected error message for invalid format
    with pytest.raises(PackitConfigException, match="not a valid format string"):
        validator.validate()


def test_valid_upstream_tag_template(tmp_path):
    config_dict = {
        "upstream_tag_template": "v{version}",  # valid format
        "specfile_path": "my_specfile.spec",  # Ensure the specfile path is valid
    }
    validator = PackageConfigValidator(
        config_content=config_dict,
        config_file_path=tmp_path / "packit.yaml",
        project_path=tmp_path,
    )
    # This should not raise any exception
    validator.validate()
