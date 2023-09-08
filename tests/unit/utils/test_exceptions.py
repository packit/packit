# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.exceptions import ensure_str


@pytest.mark.parametrize(
    "inp,exp",
    (("asd", "asd"), (b"asd", "asd"), ("🍺", "🍺"), (b"\xf0\x9f\x8d\xba", "🍺")),
    ids=("asd", "bytes-asd", "beer-str", "beer-bytes"),
)
def test_ensure_str(inp, exp):
    assert ensure_str(inp) == exp
