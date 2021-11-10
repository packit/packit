# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Tests for Upstream class
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
