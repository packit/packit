# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Tests for Distgit class
"""

import pytest

from packit.exceptions import PackitException


def test_distgit_commit_empty(distgit_instance):
    d, dg = distgit_instance
    with pytest.raises(PackitException) as ex:
        dg.commit("", "")
    assert (
        str(ex.value)
        == "No changes are present in the dist-git repo: nothing to commit."
    )


def test_get_nvr(distgit_instance):
    d, dg = distgit_instance
    nvr = dg.get_nvr("main")
    assert nvr.startswith("dist_git_remote-0.0.0-1")
