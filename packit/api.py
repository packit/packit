"""
This is the official python interface for packit.
"""

import logging
from typing import Sequence

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.upstream import Upstream

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(self, config: Config, package_config: PackageConfig) -> None:
        self.config = config
        self.package_config = package_config

    def sync_pr(self, pr_id, dist_git_branch: str, upstream_version: str = None):
        up = Upstream(config=self.config, package_config=self.package_config)

        dg = DistGit(config=self.config, package_config=self.package_config)

        up.checkout_pr(pr_id=pr_id)
        local_pr_branch = f"pull-request-{pr_id}-sync"
        # fetch and reset --hard upstream/$branch?
        dg.create_branch(dist_git_branch, base=f"remotes/origin/{dist_git_branch}", setup_tracking=True)
        dg.update_branch(dist_git_branch)
        dg.checkout_branch(dist_git_branch)

        dg.create_branch(local_pr_branch)
        dg.checkout_branch(local_pr_branch)

        dg.sync_files(up.local_project)

        patches = up.create_patches(
            upstream=upstream_version, destination=dg.local_project.working_dir
        )
        dg.add_patches_to_specfile(patches)

        description = (
            f"Upstream pr: {pr_id}\n"
            f"Upstream commit: {up.local_project.git_repo.head.commit}\n"
        )

        self.sync(
            distgit=dg,
            commit_msg=f"Sync upstream pr: {pr_id}",
            pr_title=f"Upstream pr: {pr_id}",
            pr_description=description,
            dist_git_branch="master",
            add_new_sources=False,
        )

    def sync_release(self, dist_git_branch: str, version: str = None):
        """
        Update given package in Fedora
        """
        up = Upstream(config=self.config, package_config=self.package_config)

        dg = DistGit(config=self.config, package_config=self.package_config)

        full_version = version or up.get_upstream_version()
        current_up_branch = up.active_branch
        try:
            # TODO: this is problematic, since we may overwrite stuff in the repo
            #       but the thing is that we need to do it
            #       I feel like the ideal thing to do would be to clone the repo and work in tmpdir
            # TODO: this is also naive, upstream may use different tagging scheme, e.g.
            #       release = 232, tag = v232
            up.checkout_release(full_version)

            local_pr_branch = f"{full_version}-{dist_git_branch}-update"
            # fetch and reset --hard upstream/$branch?
            logger.info(f"Using {dist_git_branch!r} dist-git branch")

            dg.create_branch(dist_git_branch, base=f"remotes/origin/{dist_git_branch}", setup_tracking=True)
            dg.update_branch(dist_git_branch)
            dg.checkout_branch(dist_git_branch)

            dg.create_branch(local_pr_branch)
            dg.checkout_branch(local_pr_branch)

            description = (
                f"Upstream tag: {full_version}\n"
                f"Upstream commit: {up.local_project.git_repo.head.commit}\n"
            )

            dg.sync_files(up.local_project)

            self.sync(
                distgit=dg,
                commit_msg=f"{full_version} upstream release",
                pr_title=f"Update to upstream release {full_version}",
                pr_description=description,
                dist_git_branch=dist_git_branch,
                commit_msg_description=description,
                add_new_sources=True,
            )
        finally:
            current_up_branch.checkout()

    def sync(
        self,
        distgit: DistGit,
        commit_msg: str,
        pr_title: str,
        pr_description: str,
        dist_git_branch: str,
        commit_msg_description: str = None,
        add_new_sources=False,
    ):

        if add_new_sources:
            # btw this is really naive: the name could be the same but the hash can be different
            # TODO: we should do something when such situation happens
            if not distgit.is_archive_in_lookaside_cache(distgit.upstream_archive_name):
                archive = distgit.download_upstream_archive()
                distgit.upload_to_lookaside_cache(archive)

        distgit.commit(title=commit_msg, msg=commit_msg_description)
        # the branch may already be up, let's push forcefully
        distgit.push_to_fork(distgit.local_project.ref, force=True)
        distgit.create_pull(
            pr_title,
            pr_description,
            source_branch=str(distgit.local_project.ref),
            target_branch=dist_git_branch,
        )

    def build(self, dist_git_branch: str, scratch: bool = False):
        """
        Build component in koji

        :param dist_git_branch: ref in dist-git
        :param scratch: should the build be a scratch build?
        """
        dg = DistGit(config=self.config, package_config=self.package_config)

        logger.info(f'using "{dist_git_branch}" dist-git branch')
        dg.create_branch(dist_git_branch, base=f"remotes/origin/{dist_git_branch}", setup_tracking=True)
        dg.update_branch(dist_git_branch)
        dg.checkout_branch(dist_git_branch)

        dg.build(scratch=scratch)

    def create_update(self, dist_git_branch: str, update_type: str,
                      update_notes: str, koji_builds: Sequence[str] = None):
        """
        Create bodhi update

        :param dist_git_branch: git ref
        :param update_type: type of the update, check CLI
        :param update_notes: documentation about the update
        :param koji_builds: list of koji builds or None (and pick latest)
        """
        logger.debug("create bodhi update, builds=%s, dg_branch=%s, type=%s",
                     koji_builds, dist_git_branch, update_type)
        dg = DistGit(config=self.config, package_config=self.package_config)
        dg.create_bodhi_update(koji_builds=koji_builds, dist_git_branch=dist_git_branch,
                               update_notes=update_notes, update_type=update_type)
