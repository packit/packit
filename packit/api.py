# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence, Callable, List, Tuple, Dict, Iterable, Optional, Union

from ogr.abstract import PullRequest
from pkg_resources import get_distribution, DistributionNotFound
from tabulate import tabulate

from packit.actions import ActionName
from packit.config import Config
from packit.config.common_package_config import CommonPackageConfig
from packit.config.package_config import find_packit_yaml, load_packit_yaml
from packit.config.package_config_validator import PackageConfigValidator
from packit.constants import SYNCING_NOTE
from packit.copr_helper import CoprHelper
from packit.distgit import DistGit
from packit.exceptions import (
    PackitException,
    PackitSRPMException,
    PackitSRPMNotFoundException,
    PackitRPMException,
    PackitRPMNotFoundException,
    PackitCoprException,
)
from packit.local_project import LocalProject
from packit.status import Status
from packit.sync import sync_files
from packit.upstream import Upstream
from packit.utils import commands
from packit.utils.extensions import assert_existence

logger = logging.getLogger(__name__)


def get_packit_version() -> str:
    try:
        return get_distribution("packitos").version
    except DistributionNotFound:
        return "NOT_INSTALLED"


class PackitAPI:
    def __init__(
        self,
        config: Config,
        package_config: Optional[
            CommonPackageConfig
        ],  # validate doesn't want PackageConfig
        upstream_local_project: LocalProject = None,
        downstream_local_project: LocalProject = None,
    ) -> None:
        self.config = config
        self.package_config: CommonPackageConfig = package_config
        self.upstream_local_project = upstream_local_project
        self.downstream_local_project = downstream_local_project

        self._up = None
        self._dg = None
        self._copr_helper: Optional[CoprHelper] = None
        self._kerberos_initialized = False

    def __repr__(self):
        return (
            "PackitAPI("
            f"config='{self.config}', "
            f"package_config='{self.package_config}', "
            f"upstream_local_project='{self.upstream_local_project}', "
            f"downstream_local_project='{self.downstream_local_project}', "
            f"up='{self.up}', "
            f"dg='{self.dg}', "
            f"copr_helper='{self.copr_helper}')"
        )

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
            self.init_kerberos_ticket()
            self._dg = DistGit(
                config=self.config,
                package_config=self.package_config,
                local_project=self.downstream_local_project,
            )
        return self._dg

    @property
    def copr_helper(self) -> CoprHelper:
        if self._copr_helper is None:
            self._copr_helper = CoprHelper(
                upstream_local_project=self.upstream_local_project
            )
        return self._copr_helper

    def sync_release(
        self,
        dist_git_branch: str,
        use_local_content=False,
        version: str = None,
        force_new_sources=False,
        upstream_ref: str = None,
        create_pr: bool = True,
        force: bool = False,
    ) -> Optional[PullRequest]:
        """
        Update given package in Fedora

        :param dist_git_branch: branch in dist-git
        :param use_local_content: don't check out anything
        :param version: upstream version to update in Fedora
        :param force_new_sources: don't check the lookaside cache and perform new-sources
        :param upstream_ref: for a source-git repo, use this ref as the latest upstream commit
        :param create_pr: create a pull request if set to True
        :param force: ignore changes in the git index

        :return created PullRequest if create_pr is True, else None
        """
        assert_existence(self.up.local_project, "Upstream local project")
        assert_existence(self.dg.local_project, "Dist-git local project")
        if self.dg.is_dirty():
            raise PackitException(
                f"The distgit repository {self.dg.local_project.working_dir} is dirty."
                f"This is not supported."
            )
        if not force and self.up.is_dirty() and not use_local_content:
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        upstream_ref = upstream_ref or self.package_config.upstream_ref
        create_pr = create_pr and self.package_config.create_pr
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
            logger.info(f"Using {dist_git_branch!r} dist-git branch.")
            self.dg.update_branch(dist_git_branch)
            self.dg.checkout_branch(dist_git_branch)

            if create_pr:
                local_pr_branch = f"{full_version}-{dist_git_branch}-update"
                self.dg.create_branch(local_pr_branch)
                self.dg.checkout_branch(local_pr_branch)

            description = (
                f"Upstream tag: {upstream_tag}\n"
                f"Upstream commit: {self.up.local_project.commit_hexsha}\n"
            )

            readme_path = self.dg.local_project.working_dir / "README.packit"
            logger.debug(f"README: {readme_path}")
            readme_path.write_text(
                SYNCING_NOTE.format(packit_version=get_packit_version())
            )

            files_to_sync = self.package_config.get_all_files_to_sync()

            if self.up.with_action(action=ActionName.prepare_files):
                comment = f"- new upstream release: {full_version}"
                try:
                    self.dg.set_specfile_content(
                        self.up.specfile, full_version, comment
                    )
                except FileNotFoundError as ex:
                    # no downstream spec file: this is either a mistake or
                    # there is no spec file in dist-git yet, hence warning
                    logger.warning(
                        f"There is not spec file downstream: {ex}, copying the one from upstream."
                    )
                    shutil.copy2(
                        self.up.absolute_specfile_path,
                        self.dg.get_absolute_specfile_path(),
                    )

                raw_sync_files = files_to_sync.get_raw_files_to_sync(
                    self.up.local_project.working_dir,
                    self.dg.local_project.working_dir,
                )

                # exclude spec, we have special plans for it
                raw_sync_files = [
                    x for x in raw_sync_files if x.src != self.up.absolute_specfile_path
                ]

                sync_files(raw_sync_files)
                if upstream_ref:
                    if self.up.with_action(action=ActionName.create_patches):
                        patches = self.up.create_patches(
                            upstream=upstream_ref,
                            destination=str(self.dg.absolute_specfile_dir),
                        )
                        self.dg.specfile_add_patches(patches)

                self._handle_sources(
                    add_new_sources=True, force_new_sources=force_new_sources
                )

            # when the action is defined, we still need to copy the files
            if self.up.has_action(action=ActionName.prepare_files):
                raw_sync_files = files_to_sync.get_raw_files_to_sync(
                    self.up.local_project.working_dir,
                    self.dg.local_project.working_dir,
                )
                sync_files(raw_sync_files)

            self.dg.commit(title=f"{full_version} upstream release", msg=description)

            new_pr = None
            if create_pr:
                new_pr = self.push_and_create_pr(
                    pr_title=f"Update to upstream release {full_version}",
                    pr_description=description,
                    dist_git_branch=dist_git_branch,
                )
            else:
                self.dg.push(refspec=f"HEAD:{dist_git_branch}")
        finally:
            if not use_local_content:
                self.up.local_project.git_repo.git.checkout(current_up_branch)
            self.dg.refresh_specfile()

        return new_pr

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
        logger.info(f"Upstream active branch: {self.up.active_branch}")

        if not force and self.up.is_dirty():
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        logger.info(f"Using {dist_git_branch!r} dist-git branch.")

        if no_pr:
            self.up.checkout_branch(upstream_branch)
        else:
            local_pr_branch = f"{dist_git_branch}-downstream-sync"
            self.up.create_branch(local_pr_branch)
            self.up.checkout_branch(local_pr_branch)

        raw_sync_files = self.package_config.synced_files.get_raw_files_to_sync(
            dest_dir=self.dg.local_project.working_dir,
            src_dir=self.up.local_project.working_dir,
        )

        reverse_raw_sync_files = [
            raw_file.reversed()
            for raw_file in raw_sync_files
            if Path(raw_file.dest).name not in exclude_files
        ]
        sync_files(reverse_raw_sync_files, fail_on_missing=False)

        if not no_pr:
            description = f"Downstream commit: {self.dg.local_project.commit_hexsha}\n"

            commit_msg = f"Sync from downstream branch {dist_git_branch!r}"
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
    ) -> PullRequest:
        # the branch may already be up, let's push forcefully
        self.dg.push_to_fork(self.dg.local_project.ref, force=True)
        return self.dg.create_pull(
            pr_title,
            pr_description,
            source_branch=self.dg.local_project.ref,
            target_branch=dist_git_branch,
        )

    def _handle_sources(self, add_new_sources, force_new_sources):
        if not (add_new_sources or force_new_sources):
            return

        make_new_sources = False
        # btw this is really naive: the name could be the same but the hash can be different
        # TODO: we should do something when such situation happens
        if force_new_sources or not self.dg.is_archive_in_lookaside_cache(
            self.dg.upstream_archive_name
        ):
            make_new_sources = True
        else:
            sources_file = self.dg.local_project.working_dir / "sources"
            if self.dg.upstream_archive_name not in sources_file.read_text():
                make_new_sources = True
        if make_new_sources:
            archive = self.dg.download_upstream_archive()
            self.init_kerberos_ticket()
            self.dg.upload_to_lookaside_cache(str(archive))

    def build(
        self,
        dist_git_branch: str,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
        from_upstream: bool = False,
    ):
        """
        Build component in Fedora infra (defaults to koji)

        :param dist_git_branch: ref in dist-git
        :param scratch: should the build be a scratch build?
        :param nowait: don't wait on build?
        :param koji_target: koji target to pick (see `koji list-targets`)
        :param from_upstream: build directly from the upstream checkout?
        """
        logger.info(f"Using {dist_git_branch!r} dist-git branch")
        self.init_kerberos_ticket()

        if from_upstream:
            srpm_path = self.create_srpm(srpm_dir=self.up.local_project.working_dir)
            return self.up.koji_build(
                scratch=scratch,
                nowait=nowait,
                koji_target=koji_target,
                srpm_path=srpm_path,
            )

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
            f"Create bodhi update, "
            f"builds={koji_builds}, dg_branch={dist_git_branch}, type={update_type}"
        )
        self.dg.create_bodhi_update(
            koji_builds=koji_builds,
            dist_git_branch=dist_git_branch,
            update_notes=update_notes,
            update_type=update_type,
        )

    def create_srpm(
        self,
        output_file: str = None,
        upstream_ref: str = None,
        srpm_dir: Union[Path, str] = None,
    ) -> Path:
        """
        Create srpm from the upstream repo

        :param upstream_ref: git ref to upstream commit
        :param output_file: path + filename where the srpm should be written, defaults to cwd
        :param srpm_dir: path to the directory where the srpm is meant to be placed
        :return: a path to the srpm
        """
        self.up.run_action(actions=ActionName.post_upstream_clone)

        try:
            self.up.prepare_upstream_for_srpm_creation(upstream_ref=upstream_ref)
        except Exception as ex:
            raise PackitSRPMException(
                f"Preparing of the upstream to the SRPM build failed: {ex}"
            ) from ex
        try:
            srpm_path = self.up.create_srpm(srpm_path=output_file, srpm_dir=srpm_dir)
        except PackitSRPMException:
            raise
        except Exception as ex:
            raise PackitSRPMException(
                f"An unexpected error occurred when creating the SRPM: {ex}"
            ) from ex

        if not srpm_path.exists():
            raise PackitSRPMNotFoundException(
                f"SRPM was created successfully, but can't be found at {srpm_path}"
            )
        return srpm_path

    def create_rpms(self, upstream_ref: str = None, rpm_dir: str = None) -> List[Path]:
        """
        Create rpms from the upstream repo

        :param upstream_ref: git ref to upstream commit
        :param rpm_dir: path to the directory where the rpm is meant to be placed
        :return: a path to the rpm
        """
        self.up.run_action(actions=ActionName.post_upstream_clone)

        try:
            self.up.prepare_upstream_for_srpm_creation(upstream_ref=upstream_ref)
        except Exception as ex:
            raise PackitRPMException(
                f"Preparing of the upstream to the RPM build failed: {ex}"
            ) from ex

        try:
            rpm_paths = self.up.create_rpms(rpm_dir=rpm_dir)
        except PackitRPMException:
            raise
        except Exception as ex:
            raise PackitRPMException(
                f"An unexpected error occurred when creating the RPMs: {ex}"
            ) from ex

        for rpm_path in rpm_paths:
            if not rpm_path.exists():
                raise PackitRPMNotFoundException(
                    f"RPM was created successfully, but can't be found at {rpm_path}"
                )
        return rpm_paths

    @staticmethod
    async def status_get_downstream_prs(status) -> List[Tuple[int, str, str]]:
        try:
            await asyncio.sleep(0)
            return status.get_downstream_prs()
        except Exception as exc:
            # https://github.com/packit/ogr/issues/67 work-around
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
    async def status_get_koji_builds(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_koji_builds()
        except Exception as exc:
            logger.error(f"Failed when getting Koji builds: {exc}")
            return {}

    @staticmethod
    async def status_get_copr_builds(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_copr_builds()
        except Exception as exc:
            logger.error(f"Failed when getting Copr builds: {exc}")
            return []

    @staticmethod
    async def status_get_updates(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_updates()
        except Exception as exc:
            logger.error(f"Failed when getting Bodhi updates: {exc}")
            return []

    @staticmethod
    async def status_main(status: Status) -> List:
        """
        Schedule repository data retrieval calls concurrently.
        :param status: status of the package
        :return: awaitable tasks
        """
        res = await asyncio.gather(
            PackitAPI.status_get_downstream_prs(status),
            PackitAPI.status_get_dg_versions(status),
            PackitAPI.status_get_up_releases(status),
            PackitAPI.status_get_koji_builds(status),
            PackitAPI.status_get_copr_builds(status),
            PackitAPI.status_get_updates(status),
        )
        return res

    def status(self) -> None:
        status = Status(self.config, self.package_config, self.up, self.dg)
        if sys.version_info >= (3, 7, 0):
            res = asyncio.run(self.status_main(status))
        else:
            # backward compatibility for Python 3.6
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(
                    asyncio.gather(
                        self.status_get_downstream_prs(status),
                        self.status_get_dg_versions(status),
                        self.status_get_up_releases(status),
                        self.status_get_koji_builds(status),
                        self.status_get_copr_builds(status),
                        self.status_get_updates(status),
                    )
                )
            finally:
                asyncio.set_event_loop(None)
                loop.close()

        (ds_prs, dg_versions, up_releases, koji_builds, copr_builds, updates) = res

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

        if koji_builds:
            logger.info("\nLatest Koji builds:")
            for branch, branch_builds in koji_builds.items():
                logger.info(f"{branch}: {branch_builds}")
        else:
            logger.info("\nNo Koji builds found.")

        if copr_builds:
            logger.info("\nLatest Copr builds:")
            logger.info(
                tabulate(copr_builds, headers=["Build ID", "Project name", "Status"])
            )
        else:
            logger.info("\nNo Copr builds found.")

    def run_copr_build(
        self,
        project: str,
        chroots: List[str],
        owner: str = None,
        description: str = None,
        instructions: str = None,
        upstream_ref: str = None,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: List[str] = None,
        additional_repos: List[str] = None,
        request_admin_if_needed: bool = False,
    ) -> Tuple[int, str]:
        """
        Submit a build to copr build system using an SRPM using the current checkout.

        :param project: name of the copr project to build
                        inside (defaults to something long and ugly)
        :param chroots: a list of COPR chroots (targets) e.g. fedora-rawhide-x86_64
        :param owner: defaults to username from copr config file
        :param description: description of the project
        :param instructions: installation instructions for the project
        :param upstream_ref: git ref to upstream commit
        :param list_on_homepage: if set, created copr project will be visible on copr's home-page
        :param preserve_project: if set, project will not be created as temporary
        :param list additional_packages: buildroot packages for the chroot [DOES NOT WORK YET]
        :param list additional_repos: buildroot additional additional_repos
        :param bool request_admin_if_needed: if we can't change the settings
                                             and are not allowed to do so
        :return: id of the created build and url to the build web page
        """
        srpm_path = self.create_srpm(
            upstream_ref=upstream_ref, srpm_dir=self.up.local_project.working_dir
        )

        owner = owner or self.copr_helper.configured_owner
        if not owner:
            raise PackitCoprException(
                "Copr owner not set. Use Copr config file or `--owner` when calling packit CLI."
            )
        logger.info(f"We will operate with COPR owner {owner}.")

        self.copr_helper.create_copr_project_if_not_exists(
            project=project,
            chroots=chroots,
            owner=owner,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            preserve_project=preserve_project,
            additional_packages=additional_packages,
            additional_repos=additional_repos,
            request_admin_if_needed=request_admin_if_needed,
        )
        logger.debug(
            f"Submitting a build to copr build system,"
            f"owner={owner}, project={project}, path={srpm_path}"
        )

        build = self.copr_helper.copr_client.build_proxy.create_from_file(
            ownername=owner, projectname=project, path=srpm_path
        )
        return build.id, self.copr_helper.copr_web_build_url(build)

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """ returns copr build state """
        return self.copr_helper.watch_copr_build(
            build_id=build_id, timeout=timeout, report_func=report_func
        )

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

    def init_kerberos_ticket(self) -> None:
        """
        Initialize the kerberos ticket if we have fas_user and keytab_path configured.

        The `kinit` command is run only once when called multiple times.
        """
        if self._kerberos_initialized:
            return
        self._run_kinit()
        self._kerberos_initialized = True

    def _run_kinit(self) -> None:
        """
        Run `kinit` if we have fas_user and keytab_path configured.
        """
        if (
            not self.config.fas_user
            or not self.config.keytab_path
            or not Path(self.config.keytab_path).is_file()
        ):
            logger.info("Won't be doing kinit, no credentials provided.")
            return

        cmd = [
            "kinit",
            f"{self.config.fas_user}@FEDORAPROJECT.ORG",
            "-k",
            "-t",
            self.config.keytab_path,
        ]

        commands.run_command_remote(
            cmd=cmd,
            error_message="Failed to init kerberos ticket:",
            fail=True,
            # this prints debug logs from kerberos to stdout
            env={"KRB5_TRACE": "/dev/stdout"},
        )

    def clean(self):
        """ clean up stuff once all the work is done """
        # command handlers have nothing to clean
        logger.debug("PackitAPI.cleanup (there are no objects to clean)")

    @staticmethod
    def validate_package_config(working_dir: Path) -> str:
        """ validate .packit.yaml on the provided path and return human readable report """
        config_path = find_packit_yaml(working_dir, try_local_dir_last=True,)
        config_content = load_packit_yaml(config_path)
        v = PackageConfigValidator(config_path, config_content)
        return v.validate()
