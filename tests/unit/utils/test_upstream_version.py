# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.utils.upstream_version import get_upstream_version, requests


@pytest.mark.parametrize(
    "package, version, exception",
    [
        ("libtiff", "4.4.0", None),
        ("tiff", "4.4.0", None),
        ("python-specfile", "0.5.0", None),
        ("specfile", "0.5.0", None),
        ("python3-specfile", None, None),
        ("mock", "3.1-1", None),
        ("packitos", "0.56.0", None),
        ("packitos", "0.56.0", requests.exceptions.SSLError),
        ("packit", None, None),
    ],
)
def test_get_upstream_version(package, version, exception):
    def mocked_get(url, params, *_, **__):
        if exception is not None:
            raise exception()
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

    if exception is None:
        assert get_upstream_version(package) == version
    else:
        assert get_upstream_version(package) is None
