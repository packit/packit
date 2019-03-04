"""
This is the official python interface for packit.
"""

import logging

from rebasehelper.versioneer import versioneers_runner

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.upstream import Upstream


logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(self, config: Config, package_config: PackageConfig) -> None:
        self.config = config
        self.package_config = package_config

    def sync_pr(self, pr_id, dist_git_branch: str, dist_git_path: str = None):
        up = Upstream(config=self.config, package_config=self.package_config)

        dg = DistGit(
            config=self.config,
            package_config=self.package_config,
            dist_git_path=dist_git_path,
        )

        up.checkout_pr(pr_id=pr_id)
        local_pr_branch = f"pull-request-{pr_id}-sync"
        # fetch and reset --hard upstream/$branch?
        dg.checkout_branch(dist_git_branch)
        dg.create_branch(local_pr_branch)
        dg.checkout_branch(local_pr_branch)

        self.sync(
            upstream=up,
            distgit=dg,
            commit_msg=f"Sync upstream pr: {pr_id}",
            pr_title=f"Upstream pr: {pr_id}",
            pr_description="description",
            dist_git_branch=dist_git_branch
        )

    def sync_release(
        self, dist_git_branch: str, dist_git_path: str = None, version: str = None
    ):
        """
        Update given package in Fedora
        """
        up = Upstream(config=self.config, package_config=self.package_config)

        dg = DistGit(
            config=self.config,
            package_config=self.package_config,
            dist_git_path=dist_git_path,
        )

        full_version = (
            version
            or versioneers_runner.run(
                versioneer=None,
                package_name=self.package_config.metadata["package_name"],
                category=None,
            )
            or up.specfile.get_full_version()
        )
        current_up_branch = up.local_project.git_repo.active_branch
        try:
            # TODO: this is problematic, since we may overwrite stuff in the repo
            #       but the thing is that we need to do it
            #       I feel like the ideal thing to do would be to clone the repo and work in tmpdir
            # TODO: this is also naive, upstream may use different tagging scheme, e.g.
            #       release = 232, tag = v232
            up.checkout_release(full_version)

            local_pr_branch = f"{full_version}-{dist_git_branch}-update"
            # fetch and reset --hard upstream/$branch?
            logger.info(f"using \"{dist_git_branch}\" dist-git branch")
            dg.checkout_branch(dist_git_branch)
            dg.create_branch(local_pr_branch)
            dg.checkout_branch(local_pr_branch)

            description = (
                f"Upstream tag: {full_version}\n"
                f"Upstream commit: {up.local_project.git_repo.head.commit}\n"
            )
            self.sync(
                upstream=up,
                distgit=dg,
                commit_msg=f"{full_version} upstream release",
                pr_title=f"Update to upstream release {full_version}",
                pr_description=description,
                dist_git_branch=dist_git_branch,
                commit_msg_description=description
            )
        finally:
            current_up_branch.checkout()

    def sync(
        self,
        upstream: Upstream,
        distgit: DistGit,
        commit_msg: str,
        pr_title: str,
        pr_description: str,
        dist_git_branch: str,
        commit_msg_description: str = None,
    ):
        distgit.sync_files(upstream.local_project)
        archive = distgit.download_upstream_archive()

        distgit.upload_to_lookaside_cache(archive)

        distgit.commit(title=commit_msg, msg=commit_msg_description)
        # the branch may already be up, let's push forcefully
        distgit.push_to_fork(distgit.local_project.ref, force=True)
        distgit.create_pull(
            pr_title,
            pr_description,
            source_branch=distgit.local_project.ref,
            target_branch=dist_git_branch,
        )
