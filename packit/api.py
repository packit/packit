# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This is the official python interface for packit.
"""

import logging
import time
import asyncio

from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence, Callable, List, Tuple, Dict

from copr.v3 import Client as CoprClient
from copr.v3.exceptions import CoprNoResultException
from tabulate import tabulate

from packit.actions import ActionName
from packit.config import Config, PackageConfig
from packit.constants import DEFAULT_COPR_OWNER, COPR2GITHUB_STATE
from packit.distgit import DistGit
from packit.exceptions import PackitException, PackitInvalidConfigException
from packit.local_project import LocalProject
from packit.status import Status
from packit.sync import sync_files
from packit.upstream import Upstream
from packit.utils import assert_existence

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(
        self,
        config: Config,
        package_config: PackageConfig,
        upstream_local_project: LocalProject,
    ) -> None:
        self.config = config
        self.package_config = package_config
        self.upstream_local_project = upstream_local_project

        self._up = None
        self._dg = None

    @property
    def up(self):
        if self._up is None:
            self._up = Upstream(
                config=self.config,
                package_config=self.package_config,
                local_project=self.upstream_local_project,
            )
        return self._up

    @property
    def dg(self):
        if self._dg is None:
            self._dg = DistGit(config=self.config, package_config=self.package_config)
        return self._dg

    def sync_pr(self, pr_id, dist_git_branch: str, upstream_version: str = None):
        assert_existence(self.dg.local_project)
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        self.up.run_action(action=ActionName.pre_sync)

        self.up.checkout_pr(pr_id=pr_id)
        self.dg.check_last_commit()

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

        if self.up.with_action(action=ActionName.create_patches):
            patches = self.up.create_patches(
                upstream=upstream_version, destination=self.dg.specfile_dir
            )
            self.dg.add_patches_to_specfile(patches)

        description = (
            f"Upstream pr: {pr_id}\n"
            f"Upstream commit: {self.up.local_project.git_repo.head.commit}\n"
        )

        self._handle_sources(add_new_sources=True, force_new_sources=False)

        raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
            Path(self.up.local_project.working_dir),
            Path(self.dg.local_project.working_dir),
        )
        sync_files(raw_sync_files)

        self.dg.commit(title=f"Sync upstream pr: {pr_id}", msg=description)

        self.push_and_create_pr(
            pr_title=f"Upstream pr: {pr_id}",
            pr_description=description,
            dist_git_branch="master",
        )

    def sync_release(
        self,
        dist_git_branch: str,
        use_local_content=False,
        version: str = None,
        force_new_sources=False,
        upstream_ref: str = None,
    ):
        """
        Update given package in Fedora
        """
        assert_existence(self.up.local_project)

        assert_existence(self.dg.local_project)
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        upstream_ref = upstream_ref or self.package_config.upstream_ref

        self.up.run_action(action=ActionName.post_upstream_clone)

        full_version = version or self.up.get_version()
        if not full_version:
            raise PackitException(
                "Could not figure out version of latest upstream release."
            )
        current_up_branch = self.up.active_branch
        try:
            # TODO: this is problematic, since we may overwrite stuff in the repo
            #       but the thing is that we need to do it
            #       I feel like the ideal thing to do would be to clone the repo and work in tmpdir
            # TODO: this is also naive, upstream may use different tagging scheme, e.g.
            #       release = 232, tag = v232
            if not use_local_content:
                self.up.checkout_release(full_version)

            self.dg.check_last_commit()

            self.up.run_action(action=ActionName.pre_sync)

            local_pr_branch = f"{full_version}-{dist_git_branch}-update"
            # fetch and reset --hard upstream/$branch?
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

            if self.up.with_action(action=ActionName.prepare_files):
                raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
                    Path(self.up.local_project.working_dir),
                    Path(self.dg.local_project.working_dir),
                )
                sync_files(raw_sync_files)
                if upstream_ref:
                    if self.up.with_action(action=ActionName.create_patches):
                        patches = self.up.create_patches(
                            upstream=upstream_ref, destination=self.dg.specfile_dir
                        )
                        self.dg.add_patches_to_specfile(patches)

                self._handle_sources(
                    add_new_sources=True, force_new_sources=force_new_sources
                )

            if self.up.has_action(action=ActionName.prepare_files):
                raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
                    Path(self.up.local_project.working_dir),
                    Path(self.dg.local_project.working_dir),
                )
                sync_files(raw_sync_files)

            self.dg.commit(title=f"{full_version} upstream release", msg=description)

            self.push_and_create_pr(
                pr_title=f"Update to upstream release {full_version}",
                pr_description=description,
                dist_git_branch=dist_git_branch,
            )
        finally:
            if not use_local_content:
                self.up.local_project.git_repo.git.checkout(current_up_branch)

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
        if not dist_git_branch:
            raise PackitException("Dist-git branch is not set.")
        if not upstream_branch:
            raise PackitException("Upstream branch is not set.")
        logger.info(f"upstream active branch {self.up.active_branch}")

        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        local_pr_branch = f"{dist_git_branch}-downstream-sync"
        logger.info(f'using "{dist_git_branch}" dist-git branch')

        self.up.create_branch(local_pr_branch)
        self.up.checkout_branch(local_pr_branch)

        raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
            Path(self.dg.local_project.working_dir),
            Path(self.up.local_project.working_dir),
        )

        sync_files(raw_sync_files)

        if not no_pr:
            description = (
                f"Downstream commit: {self.dg.local_project.git_repo.head.commit}\n"
            )

            commit_msg = f"sync from downstream branch {dist_git_branch!r}"
            pr_title = f"Update from downstream branch {dist_git_branch!r}"

            self.up.commit(title=commit_msg, msg=description)

            # the branch may already be up, let's push forcefully
            source_branch, fork_username = self.up.push(
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
                fork_username=fork_username,
            )

    def push_and_create_pr(
        self, pr_title: str, pr_description: str, dist_git_branch: str
    ):
        # the branch may already be up, let's push forcefully
        self.dg.push_to_fork(self.dg.local_project.ref, force=True)
        self.dg.create_pull(
            pr_title,
            pr_description,
            source_branch=self.dg.local_project.ref,
            target_branch=dist_git_branch,
        )

    def _handle_sources(self, add_new_sources, force_new_sources):
        if add_new_sources or force_new_sources:
            make_new_sources = False
            # btw this is really naive: the name could be the same but the hash can be different
            # TODO: we should do something when such situation happens
            if force_new_sources or not self.dg.is_archive_in_lookaside_cache(
                self.dg.upstream_archive_name
            ):
                make_new_sources = True
            else:
                sources_file = Path(self.dg.local_project.working_dir) / "sources"
                if self.dg.upstream_archive_name not in sources_file.read_text():
                    make_new_sources = True
            if make_new_sources:
                archive = self.dg.download_upstream_archive()
                self.dg.upload_to_lookaside_cache(archive)

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
        Create bodhi update

        :param dist_git_branch: git ref
        :param update_type: type of the update, check CLI
        :param update_notes: documentation about the update
        :param koji_builds: list of koji builds or None (and pick latest)
        """
        logger.debug(
            "create bodhi update, builds=%s, dg_branch=%s, type=%s",
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

    def create_srpm(
        self, output_file: str = None, upstream_ref: str = None, srpm_dir: str = None
    ) -> Path:
        """
        Create srpm from the upstream repo

        :param upstream_ref: git ref to upstream commit
        :param output_file: path + filename where the srpm should be written, defaults to cwd
        :param srpm_dir: path to the directory where the srpm is meant to be placed
        :return: a path to the srpm
        """
        self.up.run_action(action=ActionName.post_upstream_clone)

        version = upstream_ref or self.up.get_current_version()
        spec_version = self.up.get_specfile_version()

        upstream_ref = upstream_ref or self.package_config.upstream_ref

        if upstream_ref:
            # source-git code: fetch the tarball and don't check out the upstream ref
            self.up.fetch_upstream_archive()
        else:
            with self.up.local_project.git_checkout_block(ref=upstream_ref):
                # upstream repo: create the archive
                self.up.create_archive(version=upstream_ref)

        if upstream_ref:
            if self.up.with_action(action=ActionName.create_patches):
                patches = self.up.create_patches(
                    upstream=upstream_ref, destination=self.up.specfile_dir
                )
                self.up.add_patches_to_specfile(patches)

        if version != spec_version:
            try:
                self.up.set_spec_version(
                    version=version, changelog_entry="- Development snapshot"
                )
            except PackitException:
                self.up.bump_spec(
                    version=version, changelog_entry="Development snapshot"
                )
        srpm_path = self.up.create_srpm(srpm_path=output_file, srpm_dir=srpm_dir)
        return srpm_path

    @staticmethod
    async def status_get_downstream_prs(status) -> List[Tuple[int, str, str]]:
        try:
            await asyncio.sleep(0)
            return status.get_downstream_prs()
        except Exception as exc:
            # https://github.com/packit-service/ogr/issues/67 work-around
            logger.error(f"Failed when getting downstream PRs: {exc}")
            return []

    @staticmethod
    async def status_get_dg_versions(status) -> Dict:
        await asyncio.sleep(0)
        return status.get_dg_versions()

    @staticmethod
    async def status_get_up_releases(status) -> List:
        await asyncio.sleep(0)
        return status.get_up_releases()

    @staticmethod
    async def status_get_builds(status) -> Dict:
        await asyncio.sleep(0)
        return status.get_builds()

    @staticmethod
    async def status_get_updates(status) -> List:
        await asyncio.sleep(0)
        return status.get_updates()

    def status(self):
        status = Status(self.config, self.package_config, self.up, self.dg)
        loop = asyncio.get_event_loop()
        try:
            res = loop.run_until_complete(
                asyncio.gather(
                    self.status_get_downstream_prs(status),
                    self.status_get_dg_versions(status),
                    self.status_get_up_releases(status),
                    self.status_get_builds(status),
                    self.status_get_updates(status),
                )
            )
        finally:
            loop.close()
        (ds_prs, dg_versions, up_releases, builds, updates) = res

        if ds_prs:
            logger.info("\nDownstream PRs:")
            logger.info(tabulate(ds_prs, headers=["ID", "Title", "URL"]))
        else:
            logger.info("\nNo downstream PRs found.")

        if dg_versions:
            logger.info("\nDist-git versions:")
            for branch, dg_version in dg_versions.items():
                logger.info(f"{branch}: {dg_version}")
        else:
            logger.info("\nNo Dist-git versions found")

        if up_releases:
            logger.info("\nUpstream releases:")
            upstream_releases_str = "\n".join(
                f"{release.tag_name}" for release in up_releases
            )
            logger.info(upstream_releases_str)
        else:
            logger.info("\nNo upstream releases found.")

        if updates:
            logger.info("\nLatest Bodhi updates:")
            logger.info(tabulate(updates, headers=["Update", "Karma", "status"]))
        else:
            logger.info("\nNo Bodhi updates found")

        if builds:
            logger.info("\nLatest Koji builds:")
            for branch, branch_builds in builds.items():
                logger.info(f"{branch}: {branch_builds}")
        else:
            logger.info("No Koji builds found.")

    def run_copr_build(self, owner, project, chroots):
        # get info
        client = CoprClient.create_from_config_file()
        try:
            copr_proj = client.project_proxy.get(owner, project)
            # make sure or project has chroots set correctly
            if set(copr_proj.chroot_repos.keys()) != set(chroots):
                logger.info(f"Updating targets on project {owner}/{project}")
                logger.debug(f"old = {set(copr_proj.chroot_repos.keys())}")
                logger.debug(f"new = {set(chroots)}")
                client.project_proxy.edit(owner, project, chroots=chroots)
        except CoprNoResultException:
            if owner == DEFAULT_COPR_OWNER:
                logger.info(f"Copr project {owner}/{project} not found. Creating new.")
                client.project_proxy.add(
                    ownername=owner,
                    projectname=project,
                    chroots=chroots,
                    description=(
                        "Continuous builds initiated by packit service.\n"
                        "For more info check out https://packit.dev/"
                    ),
                    contact="user-cont-team@redhat.com",
                )
            else:
                raise PackitInvalidConfigException(
                    f"Copr project {owner}/{project} not found."
                )
        srpm_path = self.create_srpm(srpm_dir=self.up.local_project.working_dir)
        assert srpm_path.exists()
        logger.debug(f"owner={owner}, project={project}, path={srpm_path}")
        build = client.build_proxy.create_from_file(owner, project, srpm_path)
        return build.id, build.repo_url

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """ returns copr build state """
        client = CoprClient.create_from_config_file()
        watch_end = datetime.now() + timedelta(seconds=timeout)
        logger.debug(f"Watching copr build {build_id}")
        state_reported = ""
        while True:
            build = client.build_proxy.get(build_id)
            if build.state == state_reported:
                continue
            state_reported = build.state
            logger.debug(f"COPR build {build_id}, state = {state_reported}")
            try:
                gh_state, description = COPR2GITHUB_STATE[state_reported]
            except KeyError as exc:
                logger.error(f"COPR gave us an invalid state: {exc}")
                gh_state, description = "error", "Something went wrong."
            if report_func:
                report_func(gh_state, description)
            if gh_state != "pending":
                logger.debug(f"state is now {gh_state}, ending the watch")
                return state_reported
            if watch_end < datetime.now():
                logger.error(f"the build did not finish in time ({timeout}s)")
                report_func("error", "Build watch timeout")
                return state_reported
            time.sleep(10)
