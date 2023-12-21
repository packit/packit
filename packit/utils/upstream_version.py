# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from typing import Optional

import requests

from packit.constants import HTTP_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def get_upstream_version(package_name: str) -> Optional[str]:
    """
    Gets the latest upstream version of the specified package.

    Args:
        package_name: Package name (name of SRPM in Fedora).

    Returns:
        The latest upstream version or None if no matching project
        was found on release-monitoring.org.
    """

    def query(endpoint, **kwargs):
        try:
            response = requests.get(
                f"https://release-monitoring.org/api/{endpoint}",
                params=kwargs,
                timeout=HTTP_REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            logger.debug(f"release-monitoring.org query failed: {e!s}")
            return {}
        if not response.ok:
            return {}
        return response.json()

    if not package_name:
        return None
    result = query(f"project/Fedora/{package_name}")
    version = result.get("version")
    if not version:
        # if there is no Fedora mapping, try using package name as project name
        result = query("projects", pattern=package_name)
        projects = result.get("projects", [])
        project: dict = next(
            iter(p for p in projects if p.get("name") == package_name),
            {},
        )
        version = project.get("version")
    return version
