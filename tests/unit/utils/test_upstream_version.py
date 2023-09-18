# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.utils.upstream_version import get_upstream_version, requests


@pytest.mark.parametrize(
    "package, version",
    [
        ("libtiff", "4.4.0"),
        ("tiff", "4.4.0"),
        ("python-specfile", "0.5.0"),
        ("specfile", "0.5.0"),
        ("python3-specfile", None),
        ("mock", "3.1-1"),
        ("packitos", "0.56.0"),
        ("packit", None),
    ],
)
def test_get_upstream_version(package, version):
    def mocked_get(url, params):
        packages = {
            "libtiff": "tiff",
            "python-specfile": "specfile",
            "mock": "mock",
        }
        projects = {
            "tiff": "4.4.0",
            "specfile": "0.5.0",
            "mock": "3.1-1",
            "packitos": "0.56.0",
        }
        if url.endswith("projects"):
            project, version = next(
                iter(
                    (k, v)
                    for k, v in projects.items()
                    if k.startswith(params["pattern"])
                ),
                (None, None),
            )
            items = [{"name": project, "version": version}] if project else []
            return flexmock(ok=True, json=lambda: {"projects": items})
        package_name = url.split("/")[-1]
        project = packages.get(package_name)
        version = projects.get(project)
        if version:
            return flexmock(ok=True, json=lambda: {"version": version})
        return flexmock(ok=False)

    flexmock(requests).should_receive("get").replace_with(mocked_get)

    assert get_upstream_version(package) == version
