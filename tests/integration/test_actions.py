# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import Dict

import pytest

from packit.actions import ActionName
from packit.exceptions import PackitException


@pytest.mark.parametrize(
    "action,command,env_vars,should_raise",
    (
        (ActionName.fix_spec, "true", {}, False),
        (ActionName.fix_spec, "git this-is-not-a-command", {}, True),
        (ActionName.fix_spec, "printenv E", {"E": "e"}, False),
        (ActionName.fix_spec, "printenv E", {"X": "e"}, True),
    ),
)
def test_with_action(
    upstream_instance, action: ActionName, command, env_vars: Dict, should_raise
):
    _, upstream = upstream_instance
    upstream.package_config.actions = {action: command}
    try:
        upstream.with_action(action, env=env_vars)
    except PackitException as ex:
        if should_raise:
            assert "Command " in str(ex)
            assert command.split(" ")[0] in str(ex)
        else:
            raise


@pytest.mark.parametrize(
    "action,command,env_vars,should_raise,expected_output",
    (
        (ActionName.post_upstream_clone, "true", {}, False, ""),
        (ActionName.post_upstream_clone, "git this-is-not-a-command", {}, True, ""),
        (ActionName.post_upstream_clone, "printenv E", {"E": "e"}, False, "e\n"),
        (ActionName.post_upstream_clone, "printenv E", {"X": "e"}, True, ""),
    ),
)
def test_get_output_from_action(
    upstream_instance,
    action: ActionName,
    command,
    env_vars: Dict,
    should_raise,
    expected_output: str,
):
    _, upstream = upstream_instance
    upstream.package_config.actions = {action: command}
    try:
        out = upstream.get_output_from_action(action, env=env_vars)
    except PackitException as ex:
        if should_raise:
            assert "Command " in str(ex)
            assert command.split(" ")[0] in str(ex)
            return
        else:
            raise
    if expected_output:
        assert out[-1] == expected_output
