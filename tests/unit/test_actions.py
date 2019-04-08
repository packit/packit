# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import pytest

from packit.actions import ActionName


@pytest.mark.parametrize(
    "action,valid",
    [
        ("get-current-version", True),
        ("create-patches", True),
        ("unknown-action", False),
        ("create_patches", False),
    ],
)
def test_is_valid(action, valid):
    assert ActionName.is_valid_action(action) == valid


def test_get_possible_values():
    values = ActionName.get_possible_values()
    assert values
    assert isinstance(values, list)
    for action_value in values:
        assert isinstance(action_value, str)
        assert "_" not in action_value


@pytest.mark.parametrize(
    "action_name,result",
    [
        ("get-current-version", ActionName.get_current_version),
        ("create-patches", ActionName.create_patches),
        ("unknown-action", None),
        ("create_patches", None),
    ],
)
def test_get_action_from_name(action_name, result):
    assert ActionName.get_action_from_name(action_name) == result
