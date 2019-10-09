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

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence, Callable, List, Tuple, Dict, Iterable, Optional

from copr.v3 import Client as CoprClient
from copr.v3.exceptions import CoprNoResultException
from munch import Munch
from tabulate import tabulate

from packit.actions import ActionName
from packit.config import Config, PackageConfig
from packit.constants import COPR2GITHUB_STATE, SYNCING_NOTE
from packit.distgit import DistGit
from packit.exceptions import PackitException, PackitInvalidConfigException
from packit.local_project import LocalProject
from packit.status import Status
from packit.sync import sync_files
from packit.upstream import Upstream
from packit.utils import assert_existence, get_packit_version

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(
        self,
        config: Config,
        package_config: PackageConfig,
        upstream_local_project: LocalProject = None,
        downstream_local_project: LocalProject = None,
    ) -> None:
        self.config = config
        self.package_config = package_config
        self.upstream_local_project = upstream_local_project
        self.downstream_local_project = downstream_local_project

        self._up = None
        self._dg = None
        self._copr = None

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
            self._dg = DistGit(
                config=self.config,
                package_config=self.package_config,
                local_project=self.downstream_local_project,
            )
        return self._dg

    @property
    def copr(self):
        if self._copr is None:
            self._copr = CoprClient.create_from_config_file()
        return self._copr

    def sync_pr(self, pr_id, dist_git_branch: str, upstream_version: str = None):
        assert_existence(self.dg.local_project)
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        self.up.run_action(actions=ActionName.pre_sync)

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
                upstream=upstream_version,
                destination=str(self.dg.absolute_specfile_dir),
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
        create_pr: bool = True,
        force: bool = False,
    ):
        """
        Update given package in Fedora

        :param dist_git_branch: branch in dist-git
        :param use_local_content: don't check out anything
        :param version: upstream version to update in Fedora
        :param force_new_sources: don't check the lookaside cache and perform new-sources
        :param upstream_ref: for a source-git repo, use this ref as the latest upstream commit
        :param create_pr: create a pull request if set to True
        :param force: ignore changes in the git index
        """
        assert_existence(self.up.local_project)
        assert_existence(self.dg.local_project)
        if not force and self.up.is_dirty() and not use_local_content:
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        upstream_ref = upstream_ref or self.package_config.upstream_ref
        create_pr = create_pr or self.package_config.create_pr
        self.up.run_action(actions=ActionName.post_upstream_clone)

        full_version = version or self.up.get_version()

        if not full_version:
            raise PackitException(
                "Could not figure out version of latest upstream release."
            )
        current_up_branch = self.up.active_branch
        try:
            upstream_tag = self.up.package_config.upstream_tag_template.format(
                version=full_version
            )
            if not use_local_content:
                self.up.local_project.checkout_release(upstream_tag)

            self.dg.check_last_commit()

            self.up.run_action(actions=ActionName.pre_sync)
            self.dg.create_branch(
                dist_git_branch,
                base=f"remotes/origin/{dist_git_branch}",
                setup_tracking=True,
            )

            # fetch and reset --hard upstream/$branch?
            logger.info(f"Using {dist_git_branch!r} dist-git branch")
            self.dg.update_branch(dist_git_branch)
            self.dg.checkout_branch(dist_git_branch)

            if create_pr:
                local_pr_branch = f"{full_version}-{dist_git_branch}-update"
                self.dg.create_branch(local_pr_branch)
                self.dg.checkout_branch(local_pr_branch)

            description = (
                f"Upstream tag: {upstream_tag}\n"
                f"Upstream commit: {self.up.local_project.git_repo.head.commit}\n"
            )

            path = os.path.join(self.dg.local_project.working_dir, "README.packit")
            logger.debug(f"Path of README {path}")
            with open(path, "w") as f:
                f.write(SYNCING_NOTE.format(packit_version=get_packit_version()))

            if self.up.with_action(action=ActionName.prepare_files):
                raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
                    Path(self.up.local_project.working_dir),
                    Path(self.dg.local_project.working_dir),
                )

                # exclude spec, we have special plans for it
                raw_sync_files = [
                    x for x in raw_sync_files if x.src != self.up.absolute_specfile_path
                ]

                comment = f"- new upstream release: {full_version}"
                self.dg.set_specfile_content(self.up.specfile, full_version, comment)

                sync_files(raw_sync_files)
                if upstream_ref:
                    if self.up.with_action(action=ActionName.create_patches):
                        patches = self.up.create_patches(
                            upstream=upstream_ref,
                            destination=str(self.dg.absolute_specfile_dir),
                        )
                        self.dg.add_patches_to_specfile(patches)

                self._handle_sources(
                    add_new_sources=True, force_new_sources=force_new_sources
                )

            # when the action is defined, we still need to copy the files
            if self.up.has_action(action=ActionName.prepare_files):
                raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
                    Path(self.up.local_project.working_dir),
                    Path(self.dg.local_project.working_dir),
                )
                sync_files(raw_sync_files)

            self.dg.commit(title=f"{full_version} upstream release", msg=description)

            if create_pr:
                self.push_and_create_pr(
                    pr_title=f"Update to upstream release {full_version}",
                    pr_description=description,
                    dist_git_branch=dist_git_branch,
                )
            else:
                self.dg.push(refspec=f"HEAD:{dist_git_branch}")
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
        exclude_files: Iterable[str] = None,
        force: bool = False,
    ):
        """
        Sync content of Fedora dist-git repo back to upstream

        :param exclude_files: files that will be excluded from the sync
        :param dist_git_branch: branch in dist-git
        :param upstream_branch: upstream branch
        :param no_pr: won't create a pull request if set to True
        :param fork: forks the project if set to True
        :param remote_name: name of remote where we should push; if None, try to find a ssh_url
        :param force: ignore changes in the git index
        """
        exclude_files = exclude_files or []
        if not dist_git_branch:
            raise PackitException("Dist-git branch is not set.")
        if not upstream_branch:
            raise PackitException("Upstream branch is not set.")
        logger.info(f"upstream active branch {self.up.active_branch}")

        if not force and self.up.is_dirty():
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        logger.info(f'using "{dist_git_branch}" dist-git branch')

        if no_pr:
            self.up.checkout_branch(upstream_branch)
        else:
            local_pr_branch = f"{dist_git_branch}-downstream-sync"
            self.up.create_branch(local_pr_branch)
            self.up.checkout_branch(local_pr_branch)

        raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
            dest_dir=Path(self.dg.local_project.working_dir),
            src_dir=Path(self.up.local_project.working_dir),
        )

        reverse_raw_sync_files = [
            raw_file.reversed()
            for raw_file in raw_sync_files
            if Path(raw_file.dest).name not in exclude_files
        ]
        sync_files(reverse_raw_sync_files, fail_on_missing=False)

        if not no_pr:
            description = (
                f"Downstream commit: {self.dg.local_project.git_repo.head.commit}\n"
            )

            commit_msg = f"sync from downstream branch {dist_git_branch!r}"
            pr_title = f"Update from downstream branch {dist_git_branch!r}"

            self.up.commit(title=commit_msg, msg=description)

            # the branch may already be up, let's push forcefully
            source_branch, fork_username = self.up.push_to_fork(
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
                self.dg.upload_to_lookaside_cache(str(archive))

    def build(
        self,
        dist_git_branch: str,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
    ):
        """
        Build component in Fedora infra (defaults to koji)

        :param dist_git_branch: ref in dist-git
        :param scratch: should the build be a scratch build?
        :param nowait: don't wait on build?
        :param koji_target: koji target to pick (see `koji list-targets`)
        """
        logger.info(f"Using {dist_git_branch!r} dist-git branch")

        self.dg.create_branch(
            dist_git_branch,
            base=f"remotes/origin/{dist_git_branch}",
            setup_tracking=True,
        )

        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        self.dg.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

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
        self.up.run_action(actions=ActionName.post_upstream_clone)

        current_git_describe_version = self.up.get_current_version()
        upstream_ref = upstream_ref or self.package_config.upstream_ref
        commit = self.up.local_project.git_repo.active_branch.commit.hexsha[:8]

        if self.up.running_in_service():
            relative_to = Path(self.config.command_handler_work_dir)
        else:
            relative_to = Path.cwd()

        if upstream_ref:
            # source-git code: fetch the tarball and don't check out the upstream ref
            self.up.fetch_upstream_archive()
            source_dir = self.up.absolute_specfile_dir.relative_to(relative_to)
            if self.up.with_action(action=ActionName.create_patches):
                patches = self.up.create_patches(
                    upstream=upstream_ref,
                    destination=str(self.up.absolute_specfile_dir),
                )
                self.up.add_patches_to_specfile(patches)

            old_release = self.up.specfile.get_release_number()
            try:
                old_release_int = int(old_release)
                new_release = old_release_int + 1
            except ValueError:
                new_release = old_release
            release_to_update = f"{new_release}.g{commit}"
            msg = f"Downstream changes ({commit})"
            self.up.set_spec_version(
                release=release_to_update, changelog_entry=f"- {msg}"
            )
        else:
            archive = self.up.create_archive(version=current_git_describe_version)
            env = {
                "PACKIT_PROJECT_VERSION": current_git_describe_version,
                "PACKIT_PROJECT_COMMIT": commit,
                "PACKIT_PROJECT_ARCHIVE": archive,
            }
            if self.up.with_action(action=ActionName.fix_spec, env=env):
                self.up.fix_spec(
                    archive=archive, version=current_git_describe_version, commit=commit
                )
            if self.up.local_project.working_dir.startswith(str(relative_to)):
                source_dir = Path(self.up.local_project.working_dir).relative_to(
                    relative_to
                )
            else:
                source_dir = Path(self.up.local_project.working_dir)
        srpm_path = self.up.create_srpm(
            srpm_path=output_file, srpm_dir=srpm_dir, source_dir=source_dir
        )
        if not srpm_path.exists():
            raise PackitException(
                f"SRPM was created successfully, but can't be found at {srpm_path}"
            )
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
        try:
            await asyncio.sleep(0)
            return status.get_dg_versions()
        except Exception as exc:
            logger.error(f"Failed when getting Dist-git versions: {exc}")
            return {}

    @staticmethod
    async def status_get_up_releases(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_up_releases()
        except Exception as exc:
            logger.error(f"Failed when getting upstream releases: {exc}")
            return []

    @staticmethod
    async def status_get_builds(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_builds()
        except Exception as exc:
            logger.error(f"Failed when getting Koji builds: {exc}")
            return {}

    @staticmethod
    async def status_get_updates(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_updates()
        except Exception as exc:
            logger.error(f"Failed when getting Bodhi updates: {exc}")
            return []

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
            logger.info("\nNo Dist-git versions found.")

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
            logger.info("\nNo Bodhi updates found.")

        if builds:
            logger.info("\nLatest Koji builds:")
            for branch, branch_builds in builds.items():
                logger.info(f"{branch}: {branch_builds}")
        else:
            logger.info("No Koji builds found.")

    @staticmethod
    def _copr_web_build_url(build: Munch):
        """ Construct web frontend url because build.repo_url is not much user-friendly."""
        return (
            "https://copr.fedorainfracloud.org/coprs/"
            f"{build.ownername}/{build.projectname}/build/{build.id}/"
        )

    def run_copr_build(
        self,
        project: str,
        chroots: List[str],
        owner: str = None,
        description: str = None,
        instructions: str = None,
    ) -> Tuple[int, str]:
        """
        Submit a build to copr build system using an SRPM using the current checkout.

        :param project: name of the copr project to build
                        inside (defaults to something long and ugly)
        :param chroots: a list of COPR chroots (targets) e.g. fedora-rawhide-x86_64
        :param owner: defaults to username from copr config file
        :param description: description of the project
        :param instructions: installation instructions for the project
        :return: id of the created build and url to the build web page
        """
        # get info
        configured_owner = self.copr.config.get("username")
        owner = owner or configured_owner
        try:
            copr_proj = self.copr.project_proxy.get(owner, project)
            # make sure or project has chroots set correctly
            if set(copr_proj.chroot_repos.keys()) != set(chroots):
                logger.info(f"Updating targets on project {owner}/{project}")
                logger.debug(f"old = {set(copr_proj.chroot_repos.keys())}")
                logger.debug(f"new = {set(chroots)}")
                self.copr.project_proxy.edit(
                    owner,
                    project,
                    chroots=chroots,
                    description=description,
                    instructions=instructions,
                )
        except CoprNoResultException:
            if owner == configured_owner:
                logger.info(f"Copr project {owner}/{project} not found. Creating new.")
                self.copr.project_proxy.add(
                    ownername=owner,
                    projectname=project,
                    chroots=chroots,
                    description=(
                        description
                        or "Continuous builds initiated by packit service.\n"
                        "For more info check out https://packit.dev/"
                    ),
                    contact="https://github.com/packit-service/packit/issues",
                    # don't show project on Copr homepage
                    unlisted_on_hp=True,
                    # delete project after the specified period of time
                    delete_after_days=60,
                    instructions=instructions
                    or "You can check out the upstream project"
                    f"{self.upstream_local_project.git_url} to find out how to consume these"
                    "builds. This copr project is created and handled by the packit project"
                    "(https://packit.dev/).",
                )
            else:
                raise PackitInvalidConfigException(
                    f"Copr project {owner}/{project} not found."
                )
        srpm_path = self.create_srpm(srpm_dir=self.up.local_project.working_dir)
        logger.debug(f"owner={owner}, project={project}, path={srpm_path}")
        build = self.copr.build_proxy.create_from_file(owner, project, srpm_path)
        return build.id, self._copr_web_build_url(build)

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """ returns copr build state """
        watch_end = datetime.now() + timedelta(seconds=timeout)
        logger.debug(f"Watching copr build {build_id}")
        state_reported = ""
        while True:
            build = self.copr.build_proxy.get(build_id)
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
                report_func(
                    gh_state,
                    description,
                    build_id=build.id,
                    url=self._copr_web_build_url(build),
                )
            if gh_state != "pending":
                logger.debug(f"state is now {gh_state}, ending the watch")
                return state_reported
            if datetime.now() > watch_end:
                logger.error(f"the build did not finish in time ({timeout}s)")
                report_func("error", "Build watch timeout")
                return state_reported
            time.sleep(10)

    @staticmethod
    def push_bodhi_update(update_alias: str):
        from bodhi.client.bindings import BodhiClient, UpdateNotFound

        b = BodhiClient()
        try:
            response = b.request(update=update_alias, request="stable")
            logger.debug(f"Bodhi response:\n{response}")
            logger.info(
                f"Bodhi update {response['alias']} pushed to stable:\n"
                f"- {response['url']}\n"
                f"- stable_karma: {response['stable_karma']}\n"
                f"- unstable_karma: {response['unstable_karma']}\n"
                f"- notes:\n{response['notes']}\n"
            )
        except UpdateNotFound:
            logger.error("Update was not found.")

    def get_testing_updates(self, update_alias: Optional[str]) -> List:
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        results = b.query(
            alias=update_alias,
            packages=self.dg.package_config.downstream_package_name,
            status="testing",
        )["updates"]
        logger.debug("Bodhi updates with status 'testing' fetched.")

        return results

    @staticmethod
    def days_in_testing(update) -> int:
        if update.get("date_testing"):
            date_testing = datetime.strptime(
                update["date_testing"], "%Y-%m-%d %H:%M:%S"
            )
            return (datetime.utcnow() - date_testing).days
        return 0

    def push_updates(self, update_alias: Optional[str] = None):
        updates = self.get_testing_updates(update_alias)
        if not updates:
            logger.info("No testing updates found.")
        for update in updates:
            if self.days_in_testing(update) >= update["stable_days"]:
                self.push_bodhi_update(update["alias"])
            else:
                logger.debug(f"{update['alias']} is not ready to be pushed to stable")

    def clean(self):
        """ clean up stuff once all the work is done """
        # command handlers have nothing to clean
        logger.debug("PackitAPI.cleanup (there are no objects to clean)")
