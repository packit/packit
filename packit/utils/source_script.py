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
    """
    Returns a source script for Copr builds from dist-git repos intended
    to be submitted via Copr's BuildProxy.create_from_custom().
    The script is based on the template from the Copr user documentation:

    https://docs.copr.fedorainfracloud.org/user_documentation.html#faq-autospec

    When it comes to pull/merge requests, only GitLab MRs are currently supported.

    Args:
        package: Package name.
        dist_git: Dist-git instance to be used by dist-git-client.
        ref: Commit SHA, tag or a branch.
        pr_id: Pull/merge request ID, if applicable.
        url: Clone URL of the project containing the MR ref.
            Only needed for pull/merge requests.
        merge_pr: Whether to merge the given PR into the
            target branch before submitting a build in Copr.
            Refer to the merge_pr_in_ci config option for reference.
            Only applicable to pull/merge requests.
        target_branch: Pull/merge request target branch, if applicable.

    Returns:
        String representation of the source script to be passed to Copr
            when submitting Copr builds from a dist-git repo.

    Raises:
        PackitException: If neither ref nor pr_id is provided; if a pull/merge request
            has no URL; or if merging a pull/merge request without a target branch.
    """

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

        # TODO: these git commands are GitLab-specific
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
        # TODO: these git commands are GitLab-specific
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
    """
    Returns a source script for Copr builds from upstream repos intended
    to be submitted via Copr's BuildProxy.create_from_custom().
    The script uses Packit's prepare-sources CLI option to prepare the files
    required for an SRPM build.

    Args:
        url: Path or URL of the upstream repository.
        ref: Commit SHA, tag or a branch.
        pr_id: Pull/merge request ID, if applicable.
        merge_pr: Whether to merge the given PR into the
            target branch before submitting a build in Copr.
            Refer to the merge_pr_in_ci config option for reference.
            Only applicable to pull/merge requests.
        target_branch: Pull/merge request target branch, if applicable.
        job_config_index: Override of package config with a specific job config.
        update_release: Whether to update the package's release.
        release_suffix: Override of the default release suffix.
        package: Package name.
        merged_ref: Git ref used to identify correct most recent tag.

    Returns:
        String representation of the source script to be passed to Copr
            when submitting Copr builds from an upstream repo.
    """
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
