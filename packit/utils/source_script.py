# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import Optional

from packit.constants import (
    COPR_DISTGIT_SOURCE_SCRIPT,
    COPR_SOURCE_SCRIPT,
)
from packit.exceptions import PackitException


def create_distgit_source_script(
    package: str,
    dist_git: str = "rhel",
    ref: Optional[str] = None,
    pr_id: Optional[str] = None,
    url: Optional[str] = None,
    merge_pr: Optional[bool] = True,
    target_branch: Optional[str] = None,
):
    custom_steps: str

    if pr_id and not url:
        raise PackitException(
            "Pull/merge request ID was given, but clone URL is missing.",
        )

    if pr_id and merge_pr:
        if not target_branch:
            raise PackitException(
                "The merge_pr_in_ci option is enabled, but no target branch was given, "
                "therefore Packit cannot merge this PR.",
            )

        custom_steps = "\n".join(
            [
                f"git remote add source {url}",
                "",
                f"git fetch source refs/merge-requests/{pr_id}/head:refs/packit/pr-head",
                f"git fetch origin {target_branch}:refs/packit/target",
                "",
                "git checkout --detach refs/packit/target",
                "git merge --no-ff --no-edit refs/packit/pr-head",
            ],
        )
    elif pr_id:
        custom_steps = "\n".join(
            [
                f"git remote add source {url}",
                "",
                f"git fetch source refs/merge-requests/{pr_id}/head",
                "git checkout --detach FETCH_HEAD",
            ],
        )
    elif ref:
        custom_steps = "\n".join(
            [
                f"git fetch origin {ref}",
                "git checkout --detach FETCH_HEAD",
            ],
        )

    else:
        raise PackitException(
            "No pull request ID, commit sha or tag was given when creating a custom "
            "script to be used by Copr when submitting a build from a dist-git repo.",
        )

    return COPR_DISTGIT_SOURCE_SCRIPT.format(
        package=package,
        dist_git=dist_git,
        custom_steps=custom_steps,
    )


def create_source_script(
    url: str,
    ref: Optional[str] = None,
    pr_id: Optional[str] = None,
    merge_pr: Optional[bool] = True,
    target_branch: Optional[str] = None,
    job_config_index: Optional[int] = None,
    update_release: bool = True,
    release_suffix: Optional[str] = None,
    package: Optional[str] = None,
    merged_ref: Optional[str] = None,
):
    options = []
    if ref:
        options += ["--ref", ref]
    if pr_id:
        options += ["--pr-id", pr_id, f"--{'no-' if not merge_pr else ''}merge-pr"]
        if merge_pr and target_branch:
            options += ["--target-branch", target_branch]
    if job_config_index is not None:
        options += ["--job-config-index", str(job_config_index)]
    if not update_release:
        options += ["--no-update-release"]
    if release_suffix:
        options += ["--release-suffix", f"'{release_suffix}'"]
    if merged_ref:
        options += ["--merged-ref", f"'{merged_ref}'"]

    # do not create symlinks in Copr environment
    options += ["--no-create-symlinks"]

    options += [url]
    return COPR_SOURCE_SCRIPT.format(
        package=f" -p {package}" if package else "",
        options=" ".join(options),
    )
