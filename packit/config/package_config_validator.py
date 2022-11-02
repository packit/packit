# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Dict, Union, List, Any
import logging

from marshmallow import ValidationError

from packit.config.package_config import PackageConfig, get_local_specfile_path
from packit.exceptions import PackitConfigException
from packit.sync import iter_srcs

logger = logging.getLogger(__name__)


class PackageConfigValidator:
    """Validate the content of package configuration file (for example .packit.yaml)

    Attributes:
        config_file_path: Path of the configuration file to be validated.
        content: The content of the configuration file.
        project_path: Path of the project to which the configuration file belongs.
    """

    def __init__(
        self, config_file_path: Path, config_content: Dict, project_path: Path
    ):
        self.config_file_path = config_file_path
        self.content = config_content
        self.project_path = project_path

    def validate(self) -> str:
        """Create output for PackageConfig validation."""
        schema_errors: Union[List[Any], Dict[Any, Any]] = None
        config = None
        try:
            config = PackageConfig.get_from_dict(
                self.content,
                config_file_path=str(self.config_file_path),
                search_specfile=get_local_specfile_path,
                dir=self.config_file_path.parent,
                repo_name=self.project_path.name,
            )
        except ValidationError as e:
            schema_errors = e.messages
        except PackitConfigException as e:
            return str(e)

        specfile_path = self.content.get("specfile_path", None)
        if specfile_path and not (self.project_path / specfile_path).is_file():
            logger.warning(
                f"The spec file you defined ({specfile_path}) is not "
                f"present in the repository. If it's being generated "
                f"dynamically, you can verify the functionality by "
                f"running `packit srpm` to create an SRPM "
                f"from the current checkout. If it's not being generated, "
                f"please make sure the path is correct and "
                f"the file is present."
            )

        synced_files_errors = []
        if config:
            synced_files_errors = [
                f
                for f in iter_srcs(config.files_to_sync)
                if not (self.project_path / f).exists()
            ]

        output = f"{self.config_file_path.name} does not pass validation:\n"

        if schema_errors:
            if isinstance(schema_errors, list):
                output += "\n".join(map(str, schema_errors))
            else:
                for field_name, errors in schema_errors.items():
                    output += self.validate_get_field_output(errors, field_name)

        if synced_files_errors:
            output += (
                "The following {} configured to be synced but "
                "{} not present in the repository: {}\n"
            ).format(
                *(
                    (
                        "paths are",
                        "are",
                    )
                    if (len(synced_files_errors) > 1)
                    else ("path is", "is")
                ),
                ", ".join(synced_files_errors),
            )

        if schema_errors or synced_files_errors:
            return output
        else:
            return f"{self.config_file_path.name} is valid and ready to be used"

    def validate_get_field_output(
        self,
        errors: Union[list, dict],
        field_name: str,
        field_category: str = "* field",
        level: int = 1,
    ) -> str:
        if isinstance(errors, list):
            field_output = f"{field_category} {field_name}: {errors[0]}\n"
            return field_output

        field_output = self.validate_get_field_item_output(errors, field_name, level)
        return field_output

    def validate_get_field_item_output(
        self, errors: dict, field_name: str, level: int
    ) -> str:
        index_output = f"{level * '*'} field {field_name} has an incorrect value:\n"
        level += 1
        for index, item_errors in errors.items():
            index_type_error = self.validate_get_field_output(
                item_errors,
                index,
                field_category=f"{level * '*'} value at index",
                level=level,
            )
            index_output += index_type_error
        return index_output
