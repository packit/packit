"""
This is the official python interface for packit.
"""

import logging
from pathlib import Path
from typing import Sequence

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.upstream import Upstream
from tabulate import tabulate

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(self, config: Config, package_config: PackageConfig) -> None:
        self.config = config
        self.package_config = package_config

        self._up = None
        self._dg = None

    @property
    def up(self):
        if self._up is None:
            self._up = Upstream(config=self.config, package_config=self.package_config)
        return self._up

    @property
    def dg(self):
        if self._dg is None:
            self._dg = DistGit(config=self.config, package_config=self.package_config)
        return self._dg

    def sync_pr(self, pr_id, dist_git_branch: str, upstream_version: str = None):
        self.up.checkout_pr(pr_id=pr_id)
        local_pr_branch = f"pull-request-{pr_id}-sync"
        # fetch and reset --hard upstream/$branch?
        self.dg.create_branch(
            dist_git_branch,
            base=f"remotes/origin/{dist_git_branch}",
            setup_tracking=True,
        )
        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        self.dg.create_branch(local_pr_branch)
        self.dg.checkout_branch(local_pr_branch)

        self.dg.sync_files(self.up.local_project)

        patches = self.up.create_patches(
            upstream=upstream_version, destination=self.dg.local_project.working_dir
        )
        self.dg.add_patches_to_specfile(patches)

        description = (
            f"Upstream pr: {pr_id}\n"
            f"Upstream commit: {self.up.local_project.git_repo.head.commit}\n"
        )

        self.sync(
            distgit=self.dg,
            commit_msg=f"Sync self.upstream pr: {pr_id}",
            pr_title=f"Upstream pr: {pr_id}",
            pr_description=description,
            dist_git_branch="master",
            add_new_sources=False,
        )

    def sync_release(
        self,
        dist_git_branch: str,
        use_local_content=False,
        version: str = None,
        force_new_sources=False,
    ):
        """
        Update given package in Fedora
        """
        full_version = version or self.up.get_version()
        if not full_version:
            raise PackitException(
                "Could not figure out version of latest self.upstream release."
            )
        current_up_branch = self.up.active_branch
        try:
            # TODO: this is problematic, since we may overwrite stuff in the repo
            #       but the thing is that we need to do it
            #       I feel like the ideal thing to do would be to clone the repo and work in tmpdir
            # TODO: this is also naive, self.upstream may use different tagging scheme, e.g.
            #       release = 232, tag = v232
            if not use_local_content:
                self.up.checkout_release(full_version)

            local_pr_branch = f"{full_version}-{dist_git_branch}-self.update"
            # fetch and reset --hard self.upstream/$branch?
            logger.info(f"Using {dist_git_branch!r} dist-git branch")

            self.dg.create_branch(
                dist_git_branch,
                base=f"remotes/origin/{dist_git_branch}",
                setup_tracking=True,
            )
            self.dg.update_branch(dist_git_branch)
            self.dg.checkout_branch(dist_git_branch)

            self.dg.create_branch(local_pr_branch)
            self.dg.checkout_branch(local_pr_branch)

            description = (
                f"Upstream tag: {full_version}\n"
                f"Upstream commit: {self.up.local_project.git_repo.head.commit}\n"
            )

            self.dg.sync_files(self.up.local_project)

            self.sync(
                distgit=self.dg,
                commit_msg=f"{full_version} self.upstream release",
                pr_title=f"Update to self.upstream release {full_version}",
                pr_description=description,
                dist_git_branch=dist_git_branch,
                commit_msg_description=description,
                add_new_sources=True,
                force_new_sources=force_new_sources,
            )
        finally:
            if not use_local_content:
                self.up.local_project.git_repo.git.checkout(
                    current_up_branch.checkout()
                )

    def sync_from_downstream(
        self,
        dist_git_branch: str,
        upstream_branch: str,
        no_pr: bool = False,
        fork: bool = True,
        remote_name: str = None,
    ):
        """
        Sync content of Fedora dist-git repo back to upstream

        :param dist_git_branch: branch in dist-git
        :param upstream_branch: upstream branch
        :param no_pr: won't create a pull request if set to True
        :param fork: forks the project if set to True
        :param remote_name: name of remote where we should push; if None, try to find a ssh_url
        """
        logger.info(f"upstream active branch {self.up.active_branch}")

        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        local_pr_branch = f"{dist_git_branch}-downstream-sync"
        logger.info(f'using "{dist_git_branch}" dist-git branch')

        self.up.create_branch(local_pr_branch)
        self.up.checkout_branch(local_pr_branch)

        self.up.sync_files(self.dg.local_project)

        if not no_pr:
            description = (
                f"Downstream commit: {self.dg.local_project.git_repo.head.commit}\n"
            )

            commit_msg = f"sync from downstream branch {dist_git_branch!r}"
            pr_title = f"Update from downstream branch {dist_git_branch!r}"

            self.up.commit(title=commit_msg, msg=description)

            # the branch may already be up, let's push forcefully
            source_branch = self.up.push(
                self.up.local_project.ref,
                fork=fork,
                force=True,
                remote_name=remote_name,
            )
            self.up.create_pull(
                pr_title,
                description,
                source_branch=source_branch,
                target_branch=upstream_branch,
            )

    def sync(
        self,
        distgit: DistGit,
        commit_msg: str,
        pr_title: str,
        pr_description: str,
        dist_git_branch: str,
        commit_msg_description: str = None,
        add_new_sources=False,
        force_new_sources=False,
    ):

        if add_new_sources or force_new_sources:

            make_new_sources = False

            # btw this is really naive: the name could be the same but the hash can be different
            # TODO: we should do something when such situation happens
            if force_new_sources or not distgit.is_archive_in_lookaside_cache(
                distgit.upstream_archive_name
            ):
                make_new_sources = True
            else:
                sources_file = Path(distgit.local_project.working_dir) / "sources"
                if distgit.upstream_archive_name not in sources_file.read_text():
                    make_new_sources = True

            if make_new_sources:
                archive = distgit.download_upstream_archive()
                distgit.upload_to_lookaside_cache(archive)

        distgit.commit(title=commit_msg, msg=commit_msg_description)
        # the branch may already be self.up, let's push forcefully
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
        logger.info(f"Using {dist_git_branch!r} dist-git branch")
        self.dg.create_branch(
            dist_git_branch,
            base=f"remotes/origin/{dist_git_branch}",
            setup_tracking=True,
        )
        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        self.dg.build(scratch=scratch)

    def create_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: str,
        koji_builds: Sequence[str] = None,
    ):
        """
        Create bodhi self.update

        :param dist_git_branch: git ref
        :param update_type: type of the self.update, check CLI
        :param update_notes: documentation about the self.update
        :param koji_builds: list of koji builds or None (and pick latest)
        """
        logger.debug(
            "create bodhi self.update, builds=%s, self.dg_branch=%s, type=%s",
            koji_builds,
            dist_git_branch,
            update_type,
        )
        self.dg.create_bodhi_update(
            koji_builds=koji_builds,
            dist_git_branch=dist_git_branch,
            update_notes=update_notes,
            update_type=update_type,
        )

    def create_srpm(self, output_file: str = None) -> Path:
        """
        Create srpm from the self.upstream repo

        :param output_file: path + filename where the srpm should be written, defaults to cwd
        :return: a path to the srpm
        """
        version = self.up.get_current_version()
        spec_version = self.up.get_specfile_version()
        self.up.create_archive()
        if version != spec_version:
            try:
                self.up.set_spec_version(
                    version=version, changelog_entry="- Development snapshot"
                )
            except PackitException:
                self.up.bump_spec(
                    version=version, changelog_entry="Development snapshot"
                )
        srpm_path = self.up.create_srpm(srpm_path=output_file)
        return srpm_path

    def status(self):

        up = Upstream(config=self.config, package_config=self.package_config)
        dg = DistGit(config=self.config, package_config=self.package_config)

        pr_list = dg.local_project.git_project.get_pr_list()
        if len(pr_list) > 0:
            pr_list = pr_list[:3] if len(pr_list) > 3 else pr_list  # take last 3 PRs
            logger.info("Downstream PRs:")
            table = [[pr.id, pr.title, pr.url] for pr in pr_list]
            logger.info(tabulate(table, headers=["ID", "Title", "URL"]))
        else:
            logger.info("Downstream PRs: No open PRs.")

        logger.info("\nDist-git versions:")
        branches = dg.local_project.git_project.get_branches()
        for branch in branches:
            try:
                dg.checkout_branch(branch)
                logger.info(f"{branch}: {dg.specfile.get_version()}")
            except PackitException:
                logger.info(f"Branch {branch} doesn't exists.")

        logger.info("\nGitHub upstream releases:")
        if up.local_project.git_project is None:
            logger.info("Failed to obtain latest releases from upstream!")
        else:
            latest_releases = up.local_project.git_project.get_releases()
            # take last five releases
            latest_releases = (
                latest_releases[:5] if len(latest_releases) > 5 else latest_releases
            )
            upstream_releases_str = "\n".join(
                f"#{release.tag_name}" for release in latest_releases
            )
            logger.info(upstream_releases_str)

        logger.info("\nLatest builds:")
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        builds_d = b.latest_builds(dg.package_name)

        # there is no master tag in koji
        branches.remove("master")
        for branch in branches:
            koji_tag = f"{branch}-updates-candidate"
            try:
                koji_builds = [builds_d[koji_tag]]
                # take last three builds
                koji_builds = koji_builds[:3] if len(koji_builds) > 5 else koji_builds
                koji_builds_str = "\n".join(f" - {b}" for b in koji_builds)
                logger.info(f"{branch}:\n{koji_builds_str}")
            except KeyError:
                logger.info(f"{branch}: No builds.")

        logger.info("\nLatest bodhi updates:")
        results = b.query(packages=dg.package_name)["updates"]
        if len(results) > 3:
            results = results[:3]

        table = [
            [
                result["title"],
                result["stable_karma"],
                result["unstable_karma"],
                result["status"],
            ]
            for result in results
        ]
        logger.info(
            tabulate(
                table, headers=["Update", "Stable karma", "Unstable karma", "status"]
            )
        )
