# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import Optional

from packit.constants import COPR_SOURCE_SCRIPT


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
