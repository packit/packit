# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Optional, Union

import requests

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from ogr.abstract import GitProject
from ogr.services.pagure import PagureService

from packit.constants import (
    ANITYA_MONITORING_CHECK_URL,
    DISTGIT_INSTANCES,
    HTTP_REQUEST_TIMEOUT,
)

LEGACY_STATUS_MAP = {
    "no-monitoring": {
        "monitoring": False,
        "bugzilla": False,
        "all_versions": False,
        "stable_only": False,
        "scratch_build": False,
    },
    "monitoring": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": False,
        "stable_only": False,
        "scratch_build": False,
    },
    "monitoring-with-scratch": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": False,
        "stable_only": False,
        "scratch_build": True,
    },
    "monitoring-all": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": True,
        "stable_only": False,
        "scratch_build": False,
    },
    "monitoring-all-scratch": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": True,
        "stable_only": False,
        "scratch_build": True,
    },
    "monitoring-stable": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": False,
        "stable_only": True,
        "scratch_build": False,
    },
    "monitoring-stable-scratch": {
        "monitoring": True,
        "bugzilla": True,
        "all_versions": False,
        "stable_only": True,
        "scratch_build": True,
    },
}


@dataclass
class MonitoringMetadata:
    monitoring: bool = False
    bugzilla: bool = True
    all_versions: bool = False
    stable_only: bool = False
    scratch_build: bool = False


logger = logging.getLogger(__name__)


def get_monitoring_metadata(
    package_or_project: Union[str, GitProject],
) -> Optional[MonitoringMetadata]:
    """
    Fetches monitoring metadata for a package from dist-git.

    First tries to read monitoring.toml from the dist-git repo.
    If not found, falls back to the legacy Anitya API.

    Args:
        package_or_project: Either the package name (str) or an ogr
            GitProject for the dist-git repo.

    Returns:
        MonitoringMetadata or None if the metadata cannot be fetched.
    """
    if isinstance(package_or_project, str):
        package_name = package_or_project
        instance = DISTGIT_INSTANCES["fedpkg"]
        service = PagureService(instance_url=f"https://{instance.hostname}")
        project = service.get_project(repo=package_name, namespace=instance.namespace)
    else:
        project = package_or_project
        package_name = project.repo

    # Try monitoring.toml first
    try:
        content = project.get_file_content("monitoring.toml", ref="rawhide")
        data = tomllib.loads(content)
        return MonitoringMetadata(
            monitoring=data.get("monitoring", False),
            bugzilla=data.get("bugzilla", True),
            all_versions=data.get("all_versions", False),
            stable_only=data.get("stable_only", False),
            scratch_build=data.get("scratch_build", False),
        )
    except FileNotFoundError:
        logger.debug(
            f"monitoring.toml not found for package {package_name!r}, "
            f"falling back to legacy API.",
        )
    except Exception as e:
        logger.warning(
            f"Error while reading monitoring.toml for package {package_name!r}, "
            f"falling back to legacy API: {e}",
        )

    # Fall back to legacy API
    try:
        response = requests.get(
            ANITYA_MONITORING_CHECK_URL.format(package_name=package_name),
            timeout=HTTP_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        status = result.get("monitoring", "")
        fields = LEGACY_STATUS_MAP.get(status)
        if fields is None:
            logger.warning(
                f"Unknown monitoring status {status!r} for package {package_name!r}.",
            )
            return None
        return MonitoringMetadata(**fields)
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error while checking monitoring for package {package_name!r}: {e}",
        )
        return None
