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
