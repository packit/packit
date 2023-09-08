# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.utils.versions import compare_versions


@pytest.mark.parametrize(
    "a, b, result",
    [
        ("1.0", "1.0", 0),
        ("1.0", "2.0", -1),
        ("2.0", "1.0", 1),
        ("invalid", "invalid", 0),
        ("", "invalid", -1),
        ("invalid", "0.0", -1),
        ("0.0", "", 1),
    ],
)
def test_compare_versions(a, b, result):
    if result == 0:
        assert compare_versions(a, b) == result
    else:
        assert compare_versions(a, b) / result > 0
