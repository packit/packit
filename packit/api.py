"""
This is the official python interface for packit.
"""

import logging

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.upstream import Upstream

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(self, config: Config, package_config: PackageConfig):
        self.config = config
        self.package_config = package_config

    def update(self, dist_git_branch: str):
        """
        Update given package in Fedora
        """
        dg = DistGit(self.config)
        up = Upstream(self.config)
        full_version = up.specfile.get_full_version()
        local_pr_branch = f"{full_version}-update"
        # fetch and reset --hard upstream/$branch?
        logger.info(f"using \"{dist_git_branch}\" dist-git branch")
        dg.checkout_branch(dist_git_branch)
        dg.create_branch(local_pr_branch)
        dg.checkout_branch(local_pr_branch)

        dg.sync_files(up.local_project)
        archive = dg.download_upstream_archive()

        dg.upload_to_lookaside_cache(archive)

        dg.commit(f"{full_version} upstream release", "more info")
        dg.push_to_fork(local_pr_branch)
        dg.create_pull(
            f"Update to upstream release {full_version}",
            (
                f"Upstream branch: {up.local_project.git_repo.active_branch}\n"
                f"Upstream commit: {up.local_project.git_repo.head.commit}\n"
            ),
            local_pr_branch,
            dist_git_branch,
        )
