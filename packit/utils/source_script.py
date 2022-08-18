from typing import Optional

from packit.constants import COPR_SOURCE_SCRIPT


def create_source_script(
    url: str,
    ref: Optional[str] = None,
    pr_id: Optional[str] = None,
    merge_pr: Optional[bool] = True,
    target_branch: Optional[str] = None,
    job_config_index: Optional[int] = None,
    bump_version: bool = True,
    release_suffix: Optional[str] = None,
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
    if not bump_version:
        options += ["--no-bump"]
    if release_suffix:
        options += ["--release-suffix", f"'{release_suffix}'"]

    # do not create symlinks in Copr environment
    options += ["--no-create-symlinks"]

    options += [url]
    return COPR_SOURCE_SCRIPT.format(options=" ".join(options))
