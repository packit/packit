# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packit.utils.commands import run_command, run_command_remote, cwd
from packit.utils.extensions import assert_existence, nested_get
from packit.utils.logging import (
    StreamLogger,
    PackitFormatter,
    set_logging,
    commits_to_nice_str,
)
from packit.utils.repo import (
    is_git_repo,
    get_repo,
    get_namespace_and_repo_name,
    is_a_git_ref,
    git_remote_url_to_https_url,
)


__all__ = [
    run_command.__name__,
    run_command_remote.__name__,
    cwd.__name__,
    assert_existence.__name__,
    nested_get.__name__,
    StreamLogger.__name__,
    PackitFormatter.__name__,
    set_logging.__name__,
    commits_to_nice_str.__name__,
    is_git_repo.__name__,
    get_repo.__name__,
    get_namespace_and_repo_name.__name__,
    is_a_git_ref.__name__,
    git_remote_url_to_https_url.__name__,
]


def sanitize_branch_name(branch_name: str) -> str:
    """
    replace potentially problematic characters in provided string, a branch name

    e.g. copr says:
        Name must contain only letters, digits, underscores, dashes and dots.
    """
    # https://stackoverflow.com/questions/3411771/best-way-to-replace-multiple-characters-in-a-string
    offenders = "!@#$%^&*()+={[}]|\\'\":;<,>/?~`"
    for o in offenders:
        branch_name = branch_name.replace(o, "-")
    return branch_name


def sanitize_branch_name_for_rpm(branch_name: str) -> str:
    """
    rpm is picky about release: hates "/" - it's an error
    also prints a warning for "-"
    """
    offenders = "!@#$%^&*()+={[}]|\\'\":;<,>/?~`"
    for o in offenders:
        branch_name = branch_name.replace(o, "")
    return branch_name.replace("-", ".")
