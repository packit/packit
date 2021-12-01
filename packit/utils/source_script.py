from typing import Optional

from packit.config import JobConfig
from packit.constants import COPR_SOURCE_SCRIPT
from packit.schema import JobConfigSchema


def create_source_script(
    url: str,
    ref: Optional[str] = None,
    pr_id: Optional[str] = None,
    merge_pr: Optional[bool] = True,
    job_config: Optional[JobConfig] = None,
):
    options = []
    if ref:
        options += ["--ref", ref]
    if pr_id:
        options += ["--pr-id", pr_id, f"--{'no-' if not merge_pr else ''}merge-pr"]
    if job_config:
        job_config = JobConfigSchema().dumps(job_config)
        options += ["--job-config", f"{job_config!r}"]

    options += [url]
    return COPR_SOURCE_SCRIPT.format(options=" ".join(options))
