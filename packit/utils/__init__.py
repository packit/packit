# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packit.utils.commands import cwd, run_command, run_command_remote
from packit.utils.extensions import assert_existence, nested_get
from packit.utils.logging import (
    PackitFormatter,
    StreamLogger,
    commits_to_nice_str,
    set_logging,
)
from packit.utils.repo import (
    commit_message_file,
    get_default_branch,
    get_file_author,
    get_namespace_and_repo_name,
    get_repo,
    git_remote_url_to_https_url,
    is_a_git_ref,
    is_git_repo,
)

__all__ = [
    assert_existence.__name__,
    commit_message_file.__name__,
    commits_to_nice_str.__name__,
    cwd.__name__,
    get_default_branch.__name__,
    get_file_author.__name__,
    get_namespace_and_repo_name.__name__,
    get_repo.__name__,
    git_remote_url_to_https_url.__name__,
    is_a_git_ref.__name__,
    is_git_repo.__name__,
    nested_get.__name__,
    PackitFormatter.__name__,
    run_command.__name__,
    run_command_remote.__name__,
    set_logging.__name__,
    StreamLogger.__name__,
]
OFFENDERS = "!@#$%&*()={[}]|\\'\":;<,>/?`"


def sanitize_branch_name(branch_name: str) -> str:
    """
    replace potentially problematic characters in provided string, a branch name

    e.g. copr says:
        Name must contain only letters, digits, underscores, dashes and dots.
    """
    # https://stackoverflow.com/questions/3411771/best-way-to-replace-multiple-characters-in-a-string
    offenders = OFFENDERS + "^~+"
    for o in offenders:
        branch_name = branch_name.replace(o, "-")
    return branch_name


def sanitize_version(version: str) -> str:
    """Sanitize given string to be usable as a version.

    rpm is picky about release: hates "/" - it's an error
    also prints a warning for "-"

    Follows rules in
    https://github.com/rpm-software-management/rpm/blob/master/docs/manual/spec.md#version

    The version string consists of alphanumeric characters,
    which can optionally be segmented with the separators
    ., _ and +, plus ~ and ^
    """
    for o in OFFENDERS:
        version = version.replace(o, "")
    return version.replace("-", ".")
