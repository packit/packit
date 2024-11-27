# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
    post_modifications = "post-modifications"
    changelog_entry = "changelog-entry"
    commit_message = "commit-message"

    @classmethod
    def is_valid_action(cls, action: str) -> bool:
        return action in cls.get_possible_values()

    @classmethod
    def get_action_from_name(cls, action: str) -> Optional["ActionName"]:
        return None if not cls.is_valid_action(action) else ActionName(action)

    @classmethod
    def get_possible_values(cls):
        return [a.value for a in ActionName]
