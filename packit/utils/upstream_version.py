import requests

from typing import Optional


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
        kwargs["items_per_page"] = 1
        response = requests.get(
            f"https://release-monitoring.org/api/v2/{endpoint}", params=kwargs
        )
        if not response.ok:
            return {}
        items = response.json().get("items", [])
        return next(iter(items), {})

    if not package_name:
        return None
    result = query("packages", distribution="Fedora", name=package_name)
    # if there is no Fedora mapping, try using package name as project name
    project_name = result.get("project", package_name)
    result = query("projects", name=project_name)
    return result.get("version")
