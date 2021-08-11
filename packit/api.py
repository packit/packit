# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
This is the official python interface for packit.
"""

import asyncio
import click
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence, Callable, List, Tuple, Dict, Iterable, Optional, Union

import git

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
from packit.patches import PatchGenerator
from packit.source_git import SourceGitGenerator
from packit.status import Status
from packit.sync import sync_files, SyncFilesItem
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
        stage: bool = False,
    ) -> None:
        self.config = config
        self.package_config: CommonPackageConfig = package_config
        self.upstream_local_project = upstream_local_project
        self.downstream_local_project = downstream_local_project
        self.stage = stage

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
            f"copr_helper='{self.copr_helper}', "
            f"stage='{self.stage}')"
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
            if not self.package_config.downstream_package_name:
                if (
                    self.downstream_local_project
                    and self.downstream_local_project.working_dir
                ):
                    # the path to dist-git was passed but downstream_package_name is not set
                    # we know that package names are equal to repo names
                    self.package_config.downstream_package_name = (
                        self.downstream_local_project.working_dir.name
                    )
                    logger.info(
                        "Package name was not set, we've got it from dist-git's "
                        f"directory name: {self.package_config.downstream_package_name}"
                    )
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

    def update_dist_git(
        self,
        version: Optional[str],
        upstream_ref: Optional[str],
        add_new_sources: bool,
        force_new_sources: bool,
        upstream_tag: Optional[str],
        commit_title: str,
        commit_msg: str,
        sync_default_files: bool = True,
        pkg_tool: str = "",
    ):
        """Update a dist-git repo from an upstream (aka source-git) repo

        - copy files to be synced to dist-git
        - generate and update patch files and the spec-file
        - upload source archives to the lookaside cache
        - commit the changes to dist-git, if a commit title is defined

        Args:
            version: Upstream version to update in Fedora.
            upstream_ref: For a source-git repo, use this ref as the latest upstream commit.
            add_new_sources: Download and upload source archives.
            force_new_sources: Don't check the lookaside cache and perform new-sources.
            upstream_tag: Use the message of the commit referenced by this tag to update the
                changelog in the spec-file, if requested.
            commit_title: Commit message title (aka subject-line) in dist-git.
                Do not commit if this is false-ish.
            commit_msg: Use this commit message in dist-git.
            sync_default_files: Whether to sync the default files, that is: packit.yaml and
                the spec-file.
            pkg_tool: what tool (fedpkg/centpkg) to use upload to lookaside cache
        """
        if sync_default_files:
            synced_files = self.package_config.get_all_files_to_sync()
        else:
            synced_files = self.package_config.synced_files
        # Make all paths absolute and check that they are within
        # the working directories of the repositories.
        for item in synced_files:
            item.resolve(
                src_base=self.up.local_project.working_dir,
                dest_base=self.dg.local_project.working_dir,
            )

        if self.up.with_action(action=ActionName.prepare_files):
            synced_files = self._prepare_files_to_sync(
                synced_files=synced_files,
                full_version=version,
                upstream_tag=upstream_tag,
            )

        sync_files(synced_files)

        if upstream_ref and self.up.with_action(action=ActionName.create_patches):
            patches = self.up.create_patches(
                upstream=upstream_ref,
                destination=str(self.dg.absolute_specfile_dir),
            )
            # Undo identical patches, but don't remove them
            # from the list, so that they are added to the spec-file.
            PatchGenerator.undo_identical(patches, self.dg.local_project.git_repo)
            self.dg.specfile_add_patches(
                patches, self.package_config.patch_generation_patch_id_digits
            )

        if add_new_sources or force_new_sources:
            self._handle_sources(
                force_new_sources=force_new_sources,
                pkg_tool=pkg_tool,
            )

        if commit_title:
            self.dg.commit(title=commit_title, msg=commit_msg, prefix="")

    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        version: Optional[str] = None,
        tag: Optional[str] = None,
        use_local_content=False,
        force_new_sources=False,
        upstream_ref: Optional[str] = None,
        create_pr: bool = True,
        force: bool = False,
        create_sync_note: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sync_default_files: Optional[bool] = True,
        local_pr_branch_suffix: Optional[str] = "update",
    ) -> Optional[PullRequest]:
        """
        Update given package in dist-git

        :param dist_git_branch: branch in dist-git, defaults to repo's default branch
        :param use_local_content: don't check out anything
        :param version: upstream version to update in dist-git
        :param tag: upstream git tag
        :param force_new_sources: don't check the lookaside cache and perform new-sources
        :param upstream_ref: for a source-git repo, use this ref as the latest upstream commit
        :param create_pr: create a pull request if set to True
        :param force: ignore changes in the git index
        :param create_sync_note: whether to create a note about the sync in the dist-git repo
        :param title: title (first line) of the commit & PR
        :param description: description of the commit & PR
        :param sync_default_files: Whether to sync the default files,
                                   that is: packit.yaml and the spec-file.
        :param local_pr_branch_suffix: When create_pr is True, we push into a newly created
               branch and create a PR from it. This param specifies a suffix attached to the
               created branch name, so that we can have more PRs for the same dg branch at one time.

        :return created PullRequest if create_pr is True, else None
        """
        dist_git_branch = (
            dist_git_branch or self.dg.local_project.git_project.default_branch
        )
        # process version and tag parameters
        if version and tag:
            raise PackitException(
                "Function parameters version and tag are mutually exclusive."
            )
        elif not tag:
            version = version or self.up.get_version()
            if not version:
                raise PackitException(
                    "Could not figure out version of latest upstream release."
                )
            upstream_tag = self.up.convert_version_to_tag(version)
        else:
            upstream_tag = tag
            version = self.up.get_version_from_tag(tag)

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

        upstream_ref = self.up._expand_git_ref(
            upstream_ref or self.package_config.upstream_ref
        )
        create_pr = create_pr and self.package_config.create_pr
        self.up.run_action(actions=ActionName.post_upstream_clone)

        current_up_branch = self.up.active_branch
        try:
            # we want to check out the tag only when local_content is not set
            # and it's an actual upstream repo and not source-git
            if upstream_ref:
                logger.info(
                    "We will not check out the upstream tag "
                    "because this is a source-git repo."
                )
            elif not use_local_content:
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
                local_pr_branch = (
                    f"{version}-{dist_git_branch}-{local_pr_branch_suffix}"
                )
                self.dg.create_branch(local_pr_branch)
                self.dg.checkout_branch(local_pr_branch)

            if create_sync_note:
                readme_path = self.dg.local_project.working_dir / "README.packit"
                logger.debug(f"README: {readme_path}")
                readme_path.write_text(
                    SYNCING_NOTE.format(packit_version=get_packit_version())
                )

            description = description or (
                f"Upstream tag: {upstream_tag}\n"
                f"Upstream commit: {self.up.local_project.commit_hexsha}\n"
            )
            self.update_dist_git(
                version,
                upstream_ref,
                add_new_sources=True,
                force_new_sources=force_new_sources,
                upstream_tag=upstream_tag,
                commit_title=title or f"[packit] {version} upstream release",
                commit_msg=description,
                sync_default_files=sync_default_files,
            )

            new_pr = None
            if create_pr:
                title = title or f"Update to upstream release {version}"

                existing_pr = self.dg.existing_pr(
                    title, description.rstrip(), dist_git_branch
                )
                if not existing_pr:
                    new_pr = self.push_and_create_pr(
                        pr_title=title,
                        pr_description=description,
                        dist_git_branch=dist_git_branch,
                    )
                else:
                    logger.debug(f"PR already exists: {existing_pr.url}")
            else:
                self.dg.push(refspec=f"HEAD:{dist_git_branch}")
        finally:
            if not use_local_content and not upstream_ref:
                self.up.local_project.git_repo.git.checkout(current_up_branch)
            self.dg.refresh_specfile()
            self.dg.local_project.git_repo.git.reset("--hard", "HEAD")
        return new_pr

    def _prepare_files_to_sync(
        self, synced_files: List[SyncFilesItem], full_version: str, upstream_tag: str
    ) -> List[SyncFilesItem]:
        """Update the spec-file by setting the version and updating the changelog

        Skip everything if the changelog should be synced from upstream.

        Args:
            synced_files: A list of SyncFilesItem.
            full_version: Version to be set in the spec-file.
            upstream_tag: The commit message of this commit is going to be used
                to update the changelog in the spec-file.

        Returns:
            The list of synced files with the spec-file removed if it was updated.
        """
        if self.package_config.sync_changelog:
            return synced_files
        comment = (
            self.up.local_project.git_project.get_release(name=full_version).body
            if self.package_config.copy_upstream_release_description
            else self.up.get_commit_messages(
                after=self.up.get_last_tag(upstream_tag), before=upstream_tag
            )
        )
        try:
            self.dg.set_specfile_content(self.up.specfile, full_version, comment)
        except FileNotFoundError as ex:
            # no downstream spec file: this is either a mistake or
            # there is no spec file in dist-git yet, hence warning
            logger.warning(
                f"Unable to find a spec file in downstream: {ex}, copying the one from upstream."
            )
            shutil.copy2(
                self.up.absolute_specfile_path,
                self.dg.get_absolute_specfile_path(),
            )

        # exclude spec, we have special plans for it
        return list(
            filter(
                None, [x.drop_src(self.up.absolute_specfile_path) for x in synced_files]
            )
        )

    def sync_from_downstream(
        self,
        dist_git_branch: str = None,
        upstream_branch: str = None,
        no_pr: bool = False,
        fork: bool = True,
        remote_name: str = None,
        exclude_files: Iterable[str] = None,
        force: bool = False,
        sync_only_specfile: bool = False,
    ):
        """
        Sync content of Fedora dist-git repo back to upstream

        :param dist_git_branch: branch in dist-git, defaults to repo's default branch
        :param upstream_branch: upstream branch, defaults to repo's default branch
        :param no_pr: won't create a pull request if set to True
        :param fork: forks the project if set to True
        :param remote_name: name of remote where we should push; if None, try to find a ssh_url
        :param exclude_files: files that will be excluded from the sync
        :param force: ignore changes in the git index
        :param sync_only_specfile: whether to sync only content of specfile
        """
        exclude_files = exclude_files or []
        if not dist_git_branch:
            dist_git_branch = self.dg.local_project.git_project.default_branch
            logger.info(f"Dist-git branch not set, defaulting to {dist_git_branch!r}.")
        if not upstream_branch:
            upstream_branch = self.up.local_project.git_project.default_branch
            logger.info(f"Upstream branch not set, defaulting to {upstream_branch!r}.")
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

        files = (
            [self.package_config.get_specfile_sync_files_item(from_downstream=True)]
            if sync_only_specfile
            else self.package_config.synced_files
        )

        # Drop files to be excluded from the sync.
        for ef in exclude_files:
            files = [
                f.drop_src(ef, criteria=lambda x, y: Path(x).name == y)
                for f in files
                if f is not None
            ]
        # Make paths absolute and check if they are within the
        # working directories.
        for file in files:
            file.resolve(
                src_base=self.dg.local_project.working_dir,
                dest_base=self.up.local_project.working_dir,
            )
        sync_files(files)

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

    def _handle_sources(
        self,
        force_new_sources: bool,
        pkg_tool: str = "",
    ):
        """Download upstream archive and upload it to dist-git lookaside cache.

        Args:
            force_new_sources: Download/upload the archive even if it's
                name is already in the cache or in sources file.
                Actually, fedpkg/centpkg won't upload it if archive with the same
                name & hash is already there, so this might be useful only if
                you want to upload archive with the same name but different hash.
            pkg_tool: Tool to upload sources.
        """

        # btw this is really naive: the name could be the same but the hash can be different
        # TODO: we should do something when such situation happens
        archive_name_in_cache = self.dg.is_archive_in_lookaside_cache(
            self.dg.upstream_archive_name
        )
        sources_file = self.dg.local_project.working_dir / "sources"
        archive_name_in_sources_file = (
            sources_file.is_file()
            and self.dg.upstream_archive_name in sources_file.read_text()
        )

        if (
            archive_name_in_cache
            and archive_name_in_sources_file
            and not force_new_sources
        ):
            return

        archive = self.dg.download_upstream_archive()
        self.init_kerberos_ticket()
        self.dg.upload_to_lookaside_cache(archive=archive, pkg_tool=pkg_tool)

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
        try:
            self.up.run_action(actions=ActionName.post_upstream_clone)

            try:
                self.up.prepare_upstream_for_srpm_creation(upstream_ref=upstream_ref)
            except Exception as ex:
                raise PackitSRPMException(
                    f"Preparation of the repository for creation of an SRPM failed: {ex}"
                ) from ex
            try:
                srpm_path = self.up.create_srpm(
                    srpm_path=output_file, srpm_dir=srpm_dir
                )
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
        finally:
            self.clean()

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
            logger.debug(f"Failed when getting downstream PRs: {exc}")
            return []

    @staticmethod
    async def status_get_dg_versions(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_dg_versions()
        except Exception as exc:
            logger.debug(f"Failed when getting Dist-git versions: {exc}")
            return {}

    @staticmethod
    async def status_get_up_releases(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_up_releases()
        except Exception as exc:
            logger.debug(f"Failed when getting upstream releases: {exc}")
            return []

    @staticmethod
    async def status_get_koji_builds(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_koji_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Koji builds: {exc}")
            return {}

    @staticmethod
    async def status_get_copr_builds(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_copr_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Copr builds: {exc}")
            return []

    @staticmethod
    async def status_get_updates(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_updates()
        except Exception as exc:
            logger.debug(f"Failed when getting Bodhi updates: {exc}")
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
            click.echo("\nDownstream PRs:")
            click.echo(tabulate(ds_prs, headers=["ID", "Title", "URL"]))
        else:
            click.echo("\nNo downstream PRs found.")

        if dg_versions:
            click.echo("\nDist-git versions:")
            for branch, dg_version in dg_versions.items():
                click.echo(f"{branch: <10} {dg_version}")
        else:
            click.echo("\nNo Dist-git versions found.")

        if up_releases:
            click.echo("\nUpstream releases:")
            upstream_releases_str = "\n".join(
                f"{release.tag_name}" for release in up_releases
            )
            click.echo(upstream_releases_str)
        else:
            click.echo("\nNo upstream releases found.")

        if updates:
            click.echo("\nLatest Bodhi updates:")
            click.echo(tabulate(updates, headers=["Update", "Karma", "status"]))
        else:
            click.echo("\nNo Bodhi updates found.")

        if koji_builds:
            click.echo("\nLatest Koji builds:")
            for branch, branch_builds in koji_builds.items():
                click.echo(f"{branch: <8} {branch_builds}")
        else:
            click.echo("\nNo Koji builds found.")

        if copr_builds:
            click.echo("\nLatest Copr builds:")
            click.echo(
                tabulate(copr_builds, headers=["Build ID", "Project name", "Status"])
            )
        else:
            click.echo("\nNo Copr builds found.")

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
        """returns copr build state"""
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
            response = response["update"]
            logger.info(
                f"Bodhi update {response['alias']} ({response['title']}) pushed to stable:\n"
                f"- {response['url']}\n"
                f"- karma: {response['karma']}\n"
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

        if not self.config.pkg_tool.startswith("fedpkg"):
            # centpkg doesn't use kerberos
            return

        if (
            not self.config.fas_user
            or not self.config.keytab_path
            or not Path(self.config.keytab_path).is_file()
        ):
            logger.warning("Won't be doing kinit, no credentials provided.")
            return

        self._run_kinit()
        self._kerberos_initialized = True

    def _run_kinit(self) -> None:
        """Run `kinit`"""
        cmd = [
            "kinit",
            f"{self.config.fas_user}@{self.config.kerberos_realm}",
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
        """clean up stuff once all the work is done"""
        # this is called in p-s: Handler.clean
        if self.up.is_command_handler_set():
            self.up.command_handler.clean()
        if self.dg.is_command_handler_set():
            self.dg.command_handler.clean()

    @staticmethod
    def validate_package_config(working_dir: Path) -> str:
        """validate .packit.yaml on the provided path and return human readable report"""
        config_path = find_packit_yaml(
            working_dir,
            try_local_dir_last=True,
        )
        config_content = load_packit_yaml(config_path)
        v = PackageConfigValidator(config_path, config_content)
        return v.validate()

    def init_source_git(
        self,
        dist_git: git.Repo,
        source_git: git.Repo,
        upstream_ref: str,
        upstream_url: Optional[str] = None,
        upstream_remote: Optional[str] = None,
        pkg_tool: Optional[str] = None,
        pkg_name: Optional[str] = None,
    ):
        """
        Initialize a source-git repo from dist-git, that is: add configuration, packaging files
        needed by the distribution and transform the distribution patches into Git commits.

        Args:
            dist_git: Dist-git repository to be used for initialization.
            source_git: Git repository to be initialized as a source-git repo.
            upstream_ref: Upstream ref which is going to be the starting point of the
                source-git history. This can be a branch, tag or commit sha. It is expected
                that the current HEAD and this ref point to the same commit.
            upstream_url: Git URL to be saved in the source-git configuration.
            upstream_remote: Name of the remote from which the fetch URL is taken as the Git URL
                of the upstream project to be saved in the source-git configuration.
            pkg_tool: Packaging tool to be used to interact with the dist-git repo.
            pkg_name: Name of the package in dist-git.
        """
        sgg = SourceGitGenerator(
            config=self.config,
            dist_git=dist_git,
            source_git=source_git,
            upstream_ref=upstream_ref,
            upstream_url=upstream_url,
            upstream_remote=upstream_remote,
            pkg_tool=pkg_tool,
            pkg_name=pkg_name,
        )
        sgg.create_from_upstream()
