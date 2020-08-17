# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

from enum import Enum
from typing import Optional


class ActionName(Enum):
    """
    Name of the action.

    Can be defined by user in the per-package config file and used to overwrite the default
    implementation.

    New action needs to be added here and to the table in the
    `https://github.com/packit/packit.dev/content/docs/actions.md`.
    (Some values are also used in tests:
    - tests/unit/test_config.py
    - tests/unit/test_actions.py
    - tests/unit/test_base_git.py
    - tests/integration/test_base_git.py
    """

    post_upstream_clone = "post-upstream-clone"
    pre_sync = "pre-sync"
    create_patches = "create-patches"
    prepare_files = "prepare-files"
    create_archive = "create-archive"
    get_current_version = "get-current-version"
    fix_spec = "fix-spec-file"

    @classmethod
    def is_valid_action(cls, action: str) -> bool:
        return action in cls.get_possible_values()

    @classmethod
    def get_action_from_name(cls, action: str) -> Optional["ActionName"]:
        if not cls.is_valid_action(action):
            return None
        return ActionName(action)

    @classmethod
    def get_possible_values(cls):
        return [a.value for a in ActionName]
