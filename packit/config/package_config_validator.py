# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import Any, Union

import requests
from marshmallow import ValidationError

from packit.config import JobType
from packit.config.package_config import PackageConfig, get_local_specfile_path
from packit.constants import (
    ANITYA_MONITORING_CHECK_URL,
    DOWNSTREAM_PACKAGE_CHECK_URL,
    RELEASE_MONITORING_PACKAGE_CHECK_URL,
)
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
        self,
        config_file_path: Path,
        config_content: dict,
        project_path: Path,
        offline: bool = False,
    ):
        self.config_file_path = config_file_path
        self.content = config_content
        self.project_path = project_path
        self.offline = offline

    def validate(self) -> str:
        """Validate PackageConfig.

        Returns:
            String that the config is valid.

        Raises:
            PackitConfigException: when the config is not valid
        """
        schema_errors: Union[list[Any], dict[Any, Any]] = None
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

        specfile_path = self.content.get("specfile_path", None)
        if specfile_path and not (self.project_path / specfile_path).is_file():
            logger.warning(
                f"The spec file you defined ({specfile_path}) is not "
                f"present in the repository. If it's being generated "
                f"dynamically, you can verify the functionality by "
                f"running `packit srpm` to create an SRPM "
                f"from the current checkout. If it's not being generated, "
                f"please make sure the path is correct and "
                f"the file is present.",
            )

        files_to_sync_errors = []
        if config:
            for package_config in config.get_package_config_views().values():
                files_to_sync_errors = [
                    f
                    for f in iter_srcs(package_config.files_to_sync)
                    if not (
                        (self.project_path / package_config.paths[0] / f).exists()
                        or any(self.project_path.glob(f))
                    )
                ]  # right now we use just the first path in a monorepo package

                if not self.offline:
                    self.check_downstream_package_exists(
                        package_config.downstream_package_name,
                    )

                if (
                    any(
                        job
                        for job in package_config.get_job_views()
                        if job.type == JobType.pull_from_upstream
                    )
                ) and not self.offline:
                    package_name = package_config.downstream_package_name
                    self.check_upstream_release_monitoring_mapping_exists(package_name)
                    self.check_anitya_monitoring_enabled(package_name)

        output = f"{self.config_file_path.name} does not pass validation:\n"

        if schema_errors:
            if isinstance(schema_errors, list):
                output += "\n".join(map(str, schema_errors))
            else:
                for field_name, errors in schema_errors.items():
                    output += self.validate_get_field_output(errors, field_name)

        if files_to_sync_errors:
            output += (
                "The following {} configured to be synced but "
                "{} not present in the repository: {}\n"
            ).format(
                *(
                    (
                        "paths are",
                        "are",
                    )
                    if (len(files_to_sync_errors) > 1)
                    else ("path is", "is")
                ),
                ", ".join(files_to_sync_errors),
            )

        if schema_errors or files_to_sync_errors:
            raise PackitConfigException(output)
        return f"{self.config_file_path.name} is valid and ready to be used"

    def validate_get_field_output(
        self,
        errors: Union[list, dict],
        field_name: str,
        field_category: str = "* field",
        level: int = 1,
    ) -> str:
        if isinstance(errors, list):
            return f"{field_category} {field_name}: {errors[0]}\n"
        return self.validate_get_field_item_output(errors, field_name, level)

    def validate_get_field_item_output(
        self,
        errors: dict,
        field_name: str,
        level: int,
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

    @staticmethod
    def check_upstream_release_monitoring_mapping_exists(package_name: str):
        """
        Check whether there is mapping for the particular package in Upstream
        Release Monitoring and warn in case not.
        """
        try:
            response = requests.get(
                RELEASE_MONITORING_PACKAGE_CHECK_URL.format(package_name=package_name),
            )
            result = response.json()
            items = result.get("items")

            if not items:
                logger.warning(
                    f"No mapping for package {package_name!r} found in Upstream "
                    f"Release Monitoring. Please visit https://release-monitoring.org/ "
                    f"and create one, otherwise `pull_from_upstream` job won't be triggered.",
                )

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error while checking Upstream Release Monitoring "
                f"mapping for package {package_name!r}: {e}",
            )

    @staticmethod
    def check_anitya_monitoring_enabled(package_name: str):
        """
        Check whether the monitoring for the particular package is enabled
        and warn in case not.
        """
        try:
            response = requests.get(
                ANITYA_MONITORING_CHECK_URL.format(package_name=package_name),
            )
            result = response.json()
            if result.get("monitoring") == "no-monitoring":
                logger.warning(
                    f"Monitoring for package {package_name!r} is disabled. Please, visit "
                    f"https://src.fedoraproject.org/rpms/{package_name} and "
                    f"set `Monitoring status` on the left side to `Monitoring`, "
                    f"otherwise `pull_from_upstream` job won't be triggered.",
                )
            if result.get("monitoring") == "monitoring-with-scratch":
                logger.warning(
                    f"Monitoring for package {package_name!r} is set to "
                    f"`Monitoring and scratch builds`. Please, visit "
                    f"https://src.fedoraproject.org/rpms/{package_name} and "
                    f"set it to `Monitoring` on the left side (Monitoring status) "
                    f"to avoid duplicated scratch builds for new releases.",
                )

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error while checking monitoring for package {package_name!r}: {e}",
            )

    @staticmethod
    def check_downstream_package_exists(package_name: str):
        """
        Check whether downstream package exists.
        """
        try:
            response = requests.get(
                DOWNSTREAM_PACKAGE_CHECK_URL.format(package_name=package_name),
            )
            result = response.status_code
            if result == 404:
                logger.warning(
                    f"Package {package_name!r} does not exist. Please, make "
                    f"sure the downstream_package_name is set correctly.",
                )
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error while checking existence of package {package_name!r}: {e}",
            )
