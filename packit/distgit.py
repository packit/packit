# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import re
import tempfile
from collections.abc import Iterable, Sequence
from functools import partial
from pathlib import Path
from typing import Optional, Union

import cccolutils
import git
from bodhi.client.bindings import BodhiClientException
from lazy_object_proxy import Proxy
from ogr.abstract import PullRequest
from ogr.services.pagure import PagureProject
from specfile.utils import NEVR

from packit.base_git import PackitRepositoryBase
from packit.command_handler import CommandHandler
from packit.config import (
    Config,
    MultiplePackages,
    PackageConfig,
    get_local_package_config,
)
from packit.constants import EXISTING_BODHI_UPDATE_REGEX
from packit.exceptions import (
    PackitBodhiException,
    PackitConfigException,
    PackitException,
)
from packit.local_project import CALCULATE, LocalProject, LocalProjectBuilder
from packit.pkgtool import PkgTool
from packit.utils.bodhi import get_bodhi_client
from packit.utils.commands import cwd
from packit.utils.koji_helper import KojiHelper
from packit.utils.lookaside import LookasideCache

logger = logging.getLogger(__name__)


class DistGit(PackitRepositoryBase):
    """
    A class which interacts with dist-git and pagure-over-dist-git API.

    The logic covers git and pagure interaction, manipulation with content,
    spec files, patches and archives.

    The expectation is that this class interacts with low level APIs (ogr) and
    doesn't hold any workflow; the workflow and feeding input should be done up the stack.

    The class works with a single instance of dist-git, that's the state,
    and methods of this class interact with the local copy.
    """

    # spec files are stored in this dir in dist-git
    # this applies to Fedora and CentOS Stream 9
    spec_dir_name = ""

    # sources are stored in this dir in dist-git
    # this applies to Fedora and CentOS Stream 9
    source_dir_name = ""

    def __init__(
        self,
        config: Config,
        package_config: MultiplePackages,
        local_project: LocalProject = None,
        clone_path: Optional[str] = None,
    ):
        """
        Args:
            config: User configuration of Packit.
            package_config: Packit configuration of the package
                related to this dist-git repo.
            local_project: LocalProject object.
            clone_path: Path where the dist-git repository is cloned.
        """
        super().__init__(config=config, package_config=package_config)

        self._local_project = local_project

        self.fas_user = self.config.fas_user
        self._downstream_config: Optional[PackageConfig] = None
        self._clone_path: Optional[str] = clone_path

    def __repr__(self):
        return (
            "DistGit("
            f"config='{self.config}', "
            f"package_config='{self.package_config}', "
            f"local_project='{self.local_project}', "
            f"downstream_config='{self.downstream_config}', "
            f"absolute_specfile_path='{self.absolute_specfile_path}')"
        )

    @classmethod
    def clone(
        cls,
        config: Config,
        package_config: MultiplePackages,
        path: Path,
        branch: Optional[str] = None,
    ) -> "DistGit":
        """
        Clone dist-git repo for selected package and return this class
        Args:
            config: global packit config
            package_config: package config: downstream_package_name is utilized for cloning
            path: clone the repo to this path
            branch: optionally, check out this branch
        Returns: instance of the DistGit class
        """
        dg = cls(config, package_config)
        dg.clone_package(target_path=path, branch=branch)
        dg._local_project = LocalProjectBuilder().build(
            working_dir=path,
            git_repo=CALCULATE,
        )
        return dg

    @property
    def local_project(self):
        """return an instance of LocalProject"""
        if self._local_project is None:
            if self._clone_path:
                working_dir = self._clone_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="packit-dist-git")
                self.clone_package(target_path=tmpdir)
                working_dir = tmpdir

            self._local_project = LocalProject(
                working_dir=working_dir,
                git_url=self.package_config.dist_git_package_url,
                namespace=self.package_config.dist_git_namespace,
                repo_name=self.package_config.downstream_package_name,
                git_project=self.config.get_project(
                    url=self.package_config.dist_git_package_url,
                ),
                cache=self.repository_cache,
            )
            self._local_project.working_dir_temporary = not self._clone_path
            self._local_project.refresh_the_arguments()
            # TODO: Turn this on once p-s mocks are updated
            # builder = LocalProjectBuilder(cache=self.repository_cache)
            # self._local_project = builder.build(
            #    working_dir=working_dir,
            #    git_url=self.package_config.dist_git_package_url,
            #    namespace=self.package_config.dist_git_namespace,
            #    repo_name=self.package_config.downstream_package_name,
            #    git_project=self.config.get_project(
            #        url=self.package_config.dist_git_package_url
            #    ),
            #    git_repo=CALCULATE,
            # )
        elif not self._local_project.git_project:
            self._local_project.git_project = self.config.get_project(
                url=self.package_config.dist_git_package_url,
            )

        return self._local_project

    @property
    def command_handler(self) -> CommandHandler:
        if self._command_handler is None:
            self._command_handler = self.handler_kls(
                # so that the local_project is evaluated only when needed
                local_project=Proxy(partial(DistGit.local_project.__get__, self)),  # type: ignore
                config=self.config,
            )
        return self._command_handler

    @property
    def downstream_config(self) -> Optional[PackageConfig]:
        if not self._downstream_config:
            try:
                self._downstream_config = get_local_package_config(
                    self.local_project.working_dir,
                    repo_name=self.local_project.repo_name,
                )
            except PackitConfigException:
                return None
        return self._downstream_config

    @property
    def pkg_tool(self) -> str:
        """Returns the packaging tool. Prefers the package-level override."""
        return self.package_config.pkg_tool or self.config.pkg_tool

    def clone_package(
        self,
        target_path: Union[Path, str],
        branch: Optional[str] = None,
    ) -> None:
        """
        Clone package from dist-git, i.e. from:
        - Fedora's src.[stg.]fedoraproject.org
        - CentOS Stream's gitlab.com/redhat/centos-stream/rpms/
        - CentOS CBS's gitlab.com/CentOS/<SIG>/rpms/
        depending on configured pkg_tool: {fedpkg(default),fedpkg-stage,centpkg,cbs}

        Args:
            target_path: the name of a new directory to clone into
            branch: optional, branch to checkout
        """
        pkg_tool = PkgTool(
            fas_username=self.fas_user,
            directory=target_path,
            tool=self.package_config.pkg_tool or self.pkg_tool,
            sig=self.package_config.sig,
        )
        pkg_tool.clone(
            package_name=self.package_config.downstream_package_name,
            target_path=target_path,
            branch=branch,
            anonymous=not cccolutils.has_creds(),
        )

    def get_absolute_specfile_path(self) -> Path:
        """provide the path, don't check it"""
        if not self.package_config.downstream_package_name:
            raise PackitException(
                "Unable to find specfile in dist-git: "
                "please set downstream_package_name in your .packit.yaml",
            )
        return (
            self.local_project.working_dir
            / self.spec_dir_name
            / f"{self.package_config.downstream_package_name}.spec"
        )

    @property
    def absolute_source_dir(self) -> Path:
        """absolute path to directory with spec-file sources"""
        return self.local_project.working_dir / self.source_dir_name

    @property
    def absolute_specfile_path(self) -> Path:
        if not self._specfile_path:
            self._specfile_path = self.get_absolute_specfile_path()
            if not self._specfile_path.exists():
                raise FileNotFoundError(f"Specfile {self._specfile_path} not found.")
        return self._specfile_path

    def update_branch(self, branch_name: str):
        """
        Fetch latest commits to the selected branch; tracking needs to be set up

        :param branch_name: name of the branch to check out and fetch
        """
        logger.debug(f"About to update branch {branch_name!r}.")
        origin = self.local_project.git_repo.remote("origin")
        origin.fetch()
        try:
            head = self.local_project.git_repo.heads[branch_name]
        except IndexError as e:
            raise PackitException(f"Branch {branch_name!r} does not exist.") from e
        else:
            logger.debug(f"HEAD is now at {head.commit.hexsha} {head.commit.summary}")
        try:
            remote_ref = origin.refs[branch_name]
        except IndexError as e:
            raise PackitException(
                f"Branch {branch_name} does not exist in the origin remote.",
            ) from e
        head.set_commit(remote_ref)
        logger.debug(f"HEAD is now at {head.commit.hexsha} {head.commit.summary}")
        logger.debug(
            f"List of untracked files: {self.local_project.git_repo.untracked_files}",
        )

    def push_to_fork(
        self,
        branch_name: str,
        fork_remote_name: str = "fork",
        force: bool = False,
        sync_acls: bool = False,
    ):
        """
        push changes to a fork of the dist-git repo; they need to be committed!

        Args:
            branch_name: the branch where we push
            fork_remote_name: local name of the remote where we push to
            force: push forcefully?
            sync_acls: whether to sync the ACLs of the original repo and the fork

        """
        logger.debug(
            f"About to {'force ' if force else ''}push changes to branch {branch_name!r} "
            f"of a fork {fork_remote_name!r} of the dist-git repo.",
        )
        if fork_remote_name not in [
            remote.name for remote in self.local_project.git_repo.remotes
        ]:
            fork = self.local_project.git_project.get_fork()
            if not fork:
                self.local_project.git_project.fork_create()
                fork = self.local_project.git_project.get_fork()
            if not fork:
                raise PackitException(
                    "Unable to create a fork of repository "
                    f"{self.local_project.git_project.full_repo_name}",
                )
            if sync_acls and isinstance(self.local_project.git_project, PagureProject):
                # synchronize ACLs between original repo and fork for Pagure
                self.sync_acls(self.local_project.git_project, fork)
            fork_urls = fork.get_git_urls()
            self.local_project.git_repo.create_remote(
                name=fork_remote_name,
                url=fork_urls["ssh"],
            )

        try:
            self.push(refspec=branch_name, remote_name=fork_remote_name, force=force)
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote fork {fork_remote_name!r} using branch {branch_name!r}, "
                f"the error is:\n{ex}"
            )
            raise PackitException(msg) from ex

    def create_pull(
        self,
        pr_title: str,
        pr_description: str,
        source_branch: str,
        target_branch: str,
    ) -> PullRequest:
        """
        Create dist-git pull request using the requested branches
        """
        logger.debug(
            "About to create dist-git pull request "
            f"from {source_branch!r} to {target_branch!r}.",
        )
        project = self.local_project.git_project

        project_fork = project.get_fork()
        if not project_fork:
            project.fork_create()
            project_fork = project.get_fork()

        try:
            dist_git_pr = project_fork.create_pr(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
            )
        except Exception as ex:
            logger.error(f"There was an error while creating the PR: {ex!r}")
            raise

        logger.info(f"PR created: {dist_git_pr.url}")
        return dist_git_pr

    @property
    def upstream_archive_names(self) -> list[str]:
        """
        Sources that are considered upstream and should be uploaded to lookaside.
        Currently that's the source identified by spec_source_id (Source0 by default)
        and all other sources specified as URLs in the spec file.

        Returns:
             names of the archives, e.g. ['sen-0.6.1.tar.gz']
        """
        with self.specfile.sources() as sources:
            archive_names = [
                s.expanded_filename
                for s in sources
                if (s.remote or s.number == self.package_config.spec_source_id_number)
                and s.valid
            ]
        logger.debug(
            f"Remote sources or sources specified by spec_source_id (Source0 by default): "
            f"{archive_names}",
        )
        return archive_names

    @property
    def local_archive_names(self) -> list[str]:
        """
        Sources that are considered local (are not specified by URL).
        Source specified by spec_source_id is excluded as it is
        handled as upstream archive in upstream_archive_names.

        Returns:
             names of the archives, e.g. ['sen-0.6.1.tar.gz']
        """
        with self.specfile.sources() as sources:
            archive_names = [
                s.expanded_filename
                for s in sources
                if (
                    not s.remote
                    and s.number != self.package_config.spec_source_id_number
                )
                and s.valid
            ]
        logger.debug(
            f"Local sources (source specified by spec_source_id excluded): {archive_names}",
        )
        return archive_names

    @property
    def git_tracked_files(self) -> list[str]:
        """List of files tracked by git."""
        return [p for p, _ in self.local_project.git_repo.index.entries]

    def download_upstream_archives(self) -> list[Path]:
        """
        Fetch archives for the current upstream release defined in dist-git's spec

        :return: list of path to the archives
        """
        archives = []
        logger.info(f"Downloading archives: {self.upstream_archive_names}")
        with cwd(self.local_project.working_dir):
            self.download_remote_sources(self.pkg_tool)
        for upstream_archive_name in self.upstream_archive_names:
            archive = self.absolute_source_dir / upstream_archive_name
            if not archive.exists():
                raise PackitException(
                    f"Upstream archive was not downloaded. Check that "
                    f"{upstream_archive_name} exists in dist-git.",
                )
            archives.append(archive)
        return archives

    def download_source_files(self, pkg_tool: str = ""):
        """Download source files from the lookaside cache

        Use the pkg_tool that was specified.

        Args:
            pkg_tool: Name of the executable to be used to fetch
                the sources.
        """
        logger.info("Downloading source files from the lookaside cache...")
        pkg_tool_ = PkgTool(
            fas_username=self.config.fas_user,
            directory=self.local_project.working_dir,
            tool=pkg_tool or self.pkg_tool,
        )
        pkg_tool_.sources()

    def upload_to_lookaside_cache(
        self,
        archives: Iterable[Path],
        pkg_tool: str = "",
        offline: bool = False,
    ) -> None:
        """Upload files (archives) to the lookaside cache.

        If the archive is already uploaded, the rpkg tool doesn't do anything.

        Args:
            archive: Path to archive to upload to lookaside cache.
            pkg_tool: Optional, rpkg tool (fedpkg/centpkg/cbs) to use to upload.
            offline: Whether to use offline mode of the tool
                     (no actual upload, just local file updates).

        Raises:
            PackitException, if the upload fails.
        """
        logger.info("About to upload to lookaside cache.")
        logger.debug(f"Archives to upload: {archives}")
        pkg_tool_ = PkgTool(
            fas_username=self.config.fas_user,
            directory=self.local_project.working_dir,
            tool=pkg_tool or self.pkg_tool,
        )
        try:
            pkg_tool_.new_sources(
                sources=archives,
                offline=offline,
            )
        except Exception as ex:
            logger.error(
                f"'{pkg_tool_.tool} new-sources' failed for the following reason: {ex!r}",
            )
            raise PackitException(ex) from ex

    def is_archive_in_lookaside_cache(self, archive_path: Union[Path, str]) -> bool:
        """
        Check whether the archive is already uploaded to the lookaside cache.

        Args:
            archive_path: Path to the archive.

        Returns:
            `True`, if archive is present in the lookaside cache, `False`
            otherwise.
        """
        return LookasideCache(self.pkg_tool).is_archive_uploaded(
            self.package_config.downstream_package_name,
            archive_path,
        )

    def purge_unused_git_branches(self):
        # TODO: remove branches from merged PRs
        raise NotImplementedError("not implemented yet")

    def build(
        self,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
    ):
        """
        Perform a `fedpkg build` in the repository

        :param scratch: should the build be a scratch build?
        :param nowait: don't wait on build?
        :param koji_target: koji target to pick (see `koji list-targets`)

        Returns:
            The 'stdout' of the build command.
        """
        pkg_tool = PkgTool(
            fas_username=self.fas_user,
            directory=self.local_project.working_dir,
            tool=self.pkg_tool,
        )
        return pkg_tool.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

    @staticmethod
    def get_latest_build_for_branch(downstream_package_name, dist_git_branch):
        """Queries Koji for the latest build of a package for a dist-git branch.

        Args:
            downstream_package_name: Downstream package name.
            dist_git_branch: Associated dist-git branch.

        Returns:
            NVR of the latest build found.

        Raises:
            PackitException if there is no such build.
        """
        logger.debug(
            "Querying Koji for the latest build "
            f"of package {downstream_package_name!r} "
            f"for dist-git-branch {dist_git_branch!r}",
        )

        koji_helper = KojiHelper()
        if not (tag := koji_helper.get_candidate_tag(dist_git_branch)):
            raise PackitException(f"Failed to get candidate tag for {dist_git_branch}")
        build = koji_helper.get_latest_nvr_in_tag(downstream_package_name, tag)

        if not build:
            raise PackitException(
                f"There is no build for {downstream_package_name!r} "
                f"and koji tag {tag}",
            )
        logger.info(
            "Koji build for package "
            f"{downstream_package_name!r} and koji tag {tag}:"
            f"\n{build}",
        )
        return build

    @staticmethod
    def get_changelog_since_latest_stable_build(
        package: str,
        nvr: str,
    ) -> Optional[str]:
        """
        Retrieves changelog diff between the latest stable (tagged for a release)
        build and a build with the specified NVR.

        Args:
            package: Downstream package name.
            nvr: NVR of a build for which to get changelog diff.

        Returns:
            Changelog diff as a string or None if it wasn't possible to retrieve it.
        """
        koji_helper = KojiHelper()
        stable_tags = []
        for tag in koji_helper.get_build_tags(nvr):
            stable_tags = koji_helper.get_stable_tags(tag)
            if stable_tags:
                break
        latest_stable_nvr = None
        for tag in stable_tags:
            build = koji_helper.get_latest_nvr_in_tag(package, tag)
            if build:
                latest_stable_nvr = build
                break
        if not latest_stable_nvr or latest_stable_nvr == nvr:
            return None
        changelog = koji_helper.get_build_changelog(latest_stable_nvr)
        if not changelog:
            return None
        since = changelog[0][0]
        changelog = koji_helper.get_build_changelog(nvr)
        return koji_helper.format_changelog(changelog, since)

    def create_bodhi_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: Optional[str] = None,
        koji_builds: Optional[Sequence[str]] = None,
        sidetag: Optional[str] = None,
        bugzilla_ids: Optional[list[int]] = None,
        alias: Optional[str] = None,
    ) -> Optional[tuple[str, str]]:
        """
        Create bodhi update.

        Args:
            dist_git_branch: Git reference.
            update_type: Type of the update, check CLI.
            update_notes: Notes about the update to be displayed in Bodhi. If not specified,
              automatic update notes including a changelog diff since the latest stable build
              will be generated.
            koji_builds: List of Koji builds or `None` (picks latest).
            sidetag: Koji sidetag to create the update from.
            bugzilla_ids: List of Bugzillas that are resolved with the update.
            alias: Alias of an existing update to edit. If not specified,
              a new update will be created.

        Returns:
            Alias and URL of the update or None if the update was already created.
        """
        logger.debug(
            f"About to create a Bodhi update of type {update_type!r} from {dist_git_branch!r}",
        )

        bodhi_client = get_bodhi_client()
        # make sure we have the credentials
        bodhi_client.ensure_auth()

        if not koji_builds:
            koji_builds = [
                self.get_latest_build_for_branch(
                    self.package_config.downstream_package_name,
                    dist_git_branch=dist_git_branch,
                ),
            ]

        bugzilla_ids_from_changelog = []

        # I was thinking of verifying that the build is valid for a new bodhi update
        # but in the end it's likely a waste of resources since bodhi will tell us
        if update_notes is not None:
            rendered_note = update_notes.format(version=self.specfile.expanded_version)
        else:
            builds = ", ".join(koji_builds)
            rendered_note = f"Automatic update for {builds}."
            for nvr in koji_builds:
                package = NEVR.from_string(nvr).name
                changelog = self.get_changelog_since_latest_stable_build(package, nvr)
                if changelog:
                    rendered_note += (
                        f"\n\n##### **Changelog for {package}**\n\n```\n"
                        f"{changelog}\n```"
                    )
            bugzilla_ids_from_changelog = self.get_bugzilla_ids_from_changelog(
                rendered_note,
            )
        try:
            save_kwargs = {
                "builds": koji_builds,
                "notes": rendered_note,
                "type": update_type,
            }

            bugs = []

            if bugzilla_ids:
                bugs = list(map(str, bugzilla_ids))
            if bugzilla_ids_from_changelog:
                bugs += bugzilla_ids_from_changelog

            save_kwargs["bugs"] = bugs

            if sidetag:
                save_kwargs["from_tag"] = sidetag

            if alias:
                save_kwargs["edited"] = alias

            logger.debug(f"Saving Bodhi update with args: {save_kwargs}")

            result = bodhi_client.save(**save_kwargs)

            logger.debug(f"Bodhi response:\n{result}")
            logger.info(
                f"Bodhi update {result['alias']}:\n"
                f"- {result['url']}\n"
                f"- stable_karma: {result['stable_karma']}\n"
                f"- unstable_karma: {result['unstable_karma']}\n"
                f"- notes:\n{result['notes']}\n",
            )
            if "caveats" in result:
                for cav in result["caveats"]:
                    logger.info(f"- {cav['name']}: {cav['description']}\n")

            return result["alias"], result["url"]

        except BodhiClientException as ex:
            # don't logger.error here as it will end in sentry and it may just
            # be a transient issue: e.g. waiting for a build to be tagged
            logger.info(ex)

            # early return in case update already exists
            if re.match(EXISTING_BODHI_UPDATE_REGEX, str(ex)):
                return None

            raise PackitBodhiException(
                f"There is a problem with creating a bodhi update:\n{ex}",
            ) from ex

    def get_allowed_gpg_keys_from_downstream_config(self) -> Optional[list[str]]:
        if not self.downstream_config:
            return None

        # SAFETY: Taking first package instead of specific package should be
        # safe, since we have put a requirement on »one« ‹upstream_project_url›
        # per Packit config, i.e. even if we're dealing with a monorepo, there
        # is only »one« upstream. If there is one upstream, there is only one
        # set of GPG keys that can be allowed.
        return self.downstream_config.packages[
            self.downstream_config._first_package
        ].allowed_gpg_keys

    def get_user(self) -> Optional[str]:
        return user if (user := super().get_user()) else self.fas_user

    @staticmethod
    def get_bugzilla_ids_from_changelog(changelog: str) -> list[str]:
        """
        Find bugzilla IDs referenced in the changelog.
        """
        # https://github.com/fedora-infra/bodhi/blob/373fe7f449e66a07ab0649c369bb68b11ec6d86f/bodhi-server/bodhi/server/config.py#L317
        bz_regex = (
            r"(?:fix(?:es)?|close(?:s)?|resolve(?:s)?)(?:\:)?\s"
            r"(?:fedora|epel|rh(?:bz)?)#(\d{5,})"
        )

        bugs = [bug.group(1) for bug in re.finditer(bz_regex, changelog, re.IGNORECASE)]
        logger.debug(f"Bug IDs found in the changelog: {bugs}")
        return bugs

    def get_nvr(self, dist_git_branch: str) -> str:
        """
        Get the NVR for the branch.

        Returns:
            nvr
        """
        self.create_branch(
            dist_git_branch,
            base=f"remotes/origin/{dist_git_branch}",
            setup_tracking=True,
        )

        self.update_branch(dist_git_branch)
        self.switch_branch(dist_git_branch)
        pkg_tool = PkgTool(
            fas_username=self.fas_user,
            directory=self.local_project.working_dir,
            tool=self.pkg_tool,
        )
        return pkg_tool.verrel()
