# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

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

from pathlib import Path
from typing import Dict, Union, List, Any

from marshmallow import ValidationError

from packit.config.package_config import PackageConfig, get_local_specfile_path
from packit.exceptions import PackitConfigException


class PackageConfigValidator:
    """ validate content of .packit.yaml """

    def __init__(self, config_file_path: Path, config_content: Dict):
        self.config_file_path = config_file_path
        self.content = config_content

    def validate(self) -> str:
        """ Create output for PackageConfig validation."""
        schema_errors: Union[List[Any], Dict[Any, Any]] = None
        try:
            PackageConfig.get_from_dict(
                self.content,
                config_file_path=str(self.config_file_path),
                spec_file_path=str(
                    get_local_specfile_path(self.config_file_path.parent)
                ),
            )
        except ValidationError as e:
            schema_errors = e.messages
        except PackitConfigException as e:
            return str(e)

        if not schema_errors:
            return f"{self.config_file_path.name} is valid and ready to be used"

        output = f"{self.config_file_path.name} does not pass validation:\n"
        if isinstance(schema_errors, list):
            output += "\n".join(map(str, schema_errors))
            return output

        for field_name, errors in schema_errors.items():
            output += self.validate_get_field_output(errors, field_name)
        return output

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
