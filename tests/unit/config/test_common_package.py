# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import Optional

import pytest

from packit.config.common_package_config import _construct_dist_git_instance
from packit.constants import DISTGIT_INSTANCES
from packit.dist_git_instance import DistGitInstance


@pytest.mark.parametrize(
    "base_url, namespace, pkg_tool, sig, expected_dg_instance",
    (
        (None, None, "fedpkg", None, DISTGIT_INSTANCES["fedpkg"]),
        (None, None, "centpkg", None, DISTGIT_INSTANCES["centpkg"]),
        (
            None,
            None,
            "centpkg-sig",
            "cloud",
            DistGitInstance(
                hostname="gitlab.com",
                alternative_hostname=None,
                namespace="CentOS/cloud/rpms",
            ),
        ),
    ),
)
def test_construct_dg_instance(
    base_url: str,
    namespace: str,
    pkg_tool: str,
    sig: Optional[str],
    expected_dg_instance: DistGitInstance,
):
    assert (
        _construct_dist_git_instance(
            base_url=base_url,
            namespace=namespace,
            pkg_tool=pkg_tool,
            sig=sig,
        )
        == expected_dg_instance
    )
