# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

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
