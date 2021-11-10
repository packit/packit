# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
