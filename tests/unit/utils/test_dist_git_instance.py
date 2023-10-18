# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.constants import DISTGIT_INSTANCES
from packit.dist_git_instance import DistGitInstance

FEDORA_DG = DistGitInstance(
    hostname="src.fedoraproject.org",
    alternative_hostname="pkgs.fedoraproject.org",
    namespace="rpms",
)
CENTOS_DG = DistGitInstance(
    hostname="gitlab.com",
    alternative_hostname=None,
    namespace="redhat/centos-stream/rpms",
)


@pytest.mark.parametrize(
    "dg, url, expected",
    (
        pytest.param(FEDORA_DG, "https://src.fedoraproject.org/rpms/packit", True),
        pytest.param(FEDORA_DG, "https://src.fedoraproject.org/rpms/packit.git", True),
        pytest.param(
            FEDORA_DG,
            "ssh://mfocko@pkgs.fedoraproject.org:rpms/packit.git",
            True,
        ),
        pytest.param(FEDORA_DG, "mfocko@pkgs.fedoraproject.org:rpms/packit.git", True),
        pytest.param(FEDORA_DG, "mfocko@pkgs.fedoraproject.org:XXX/packit.git", False),
        pytest.param(CENTOS_DG, "gitlab.com/packit-service/hello-world.git", False),
        pytest.param(
            CENTOS_DG,
            "gitlab.com/packit-service/rpms/hello-world.git",
            False,
        ),
        pytest.param(
            CENTOS_DG,
            "gitlab.com/redhat/centos-stream/rpms/hello-world.git",
            True,
        ),
    ),
)
def test_has_repository(dg: DistGitInstance, url: str, expected: bool):
    assert dg.has_repository(url) == expected


@pytest.mark.parametrize(
    "url, namespace, expected",
    (
        pytest.param(
            "https://src.fedoraproject.org/",
            "rpms",
            FEDORA_DG,
            id="packit-prod / fedora-source-git-prod",
        ),
        pytest.param(
            "https://gitlab.com/",
            "redhat/centos-stream/rpms",
            CENTOS_DG,
            id="stream-prod",
        ),
    ),
)
def test_from_url_and_namespace(url: str, namespace: str, expected: DistGitInstance):
    parsed_dg_instance = DistGitInstance.from_url_and_namespace(url, namespace)

    assert parsed_dg_instance and parsed_dg_instance.hostname in (
        expected.hostname,
        expected.alternative_hostname,
    )
    assert parsed_dg_instance.namespace == expected.namespace


@pytest.mark.parametrize(
    "pkg_tool, package, expected_url",
    (
        ("fedpkg", "packit", "https://src.fedoraproject.org/rpms/packit"),
        ("centpkg", "nispor", "https://gitlab.com/redhat/centos-stream/rpms/nispor"),
        ("fedpkg-stage", "packit", "https://src.stg.fedoraproject.org/rpms/packit"),
    ),
)
def test_distgit_project_url_from_dg_constant(pkg_tool, package, expected_url):
    assert DISTGIT_INSTANCES[pkg_tool].distgit_project_url(package) == expected_url
