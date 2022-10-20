# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Sequence, List, Union

import cccolutils
import git
import requests
from bodhi.client.bindings import BodhiClientException
from fedora.client import AuthError
from koji import ClientSession
from ogr.abstract import PullRequest
from packit.base_git import PackitRepositoryBase
from packit.config import (
    Config,
    PackageConfig,
    get_local_package_config,
)
from packit.config.common_package_config import CommonPackageConfig
from packit.constants import KOJI_BASEURL
from packit.exceptions import PackitException, PackitConfigException
from packit.local_project import LocalProject
from packit.pkgtool import PkgTool
from packit.utils.bodhi import get_bodhi_client
from packit.utils.commands import cwd

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
        package_config: CommonPackageConfig,
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
        package_config: CommonPackageConfig,
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
        dg._local_project = LocalProject(working_dir=path)
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
                    url=self.package_config.dist_git_package_url
                ),
                cache=self.repository_cache,
            )
            self._local_project.working_dir_temporary = not self._clone_path
            self._local_project.refresh_the_arguments()
        elif not self._local_project.git_project:
            self._local_project.git_project = self.config.get_project(
                url=self.package_config.dist_git_package_url
            )
            self._local_project.refresh_the_arguments()

        return self._local_project

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

    def clone_package(
        self,
        target_path: Union[Path, str],
        branch: Optional[str] = None,
    ) -> None:
        """
        Clone package from dist-git, i.e. from:
        - Fedora's src.[stg.]fedoraproject.org
        - CentOS Stream's gitlab.com/redhat/centos-stream/rpms/
        depending on configured pkg_tool: {fedpkg(default),fedpkg-stage,centpkg}

        Args:
            target_path: the name of a new directory to clone into
            branch: optional, branch to checkout
        """
        pkg_tool = PkgTool(
            fas_username=self.fas_user,
            directory=target_path,
            tool=self.config.pkg_tool,
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
                "please set downstream_package_name in your .packit.yaml"
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
        except IndexError:
            raise PackitException(f"Branch {branch_name!r} does not exist.")
        try:
            remote_ref = origin.refs[branch_name]
        except IndexError:
            raise PackitException(
                f"Branch {branch_name} does not exist in the origin remote."
            )
        head.set_commit(remote_ref)

    def push_to_fork(
        self, branch_name: str, fork_remote_name: str = "fork", force: bool = False
    ):
        """
        push changes to a fork of the dist-git repo; they need to be committed!

        :param branch_name: the branch where we push
        :param fork_remote_name: local name of the remote where we push to
        :param force: push forcefully?
        """
        logger.debug(
            f"About to {'force ' if force else ''}push changes to branch {branch_name!r} "
            f"of a fork {fork_remote_name!r} of the dist-git repo."
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
                    f"{self.local_project.git_project.full_repo_name}"
                )
            fork_urls = fork.get_git_urls()
            self.local_project.git_repo.create_remote(
                name=fork_remote_name, url=fork_urls["ssh"]
            )

        try:
            self.push(refspec=branch_name, remote_name=fork_remote_name, force=force)
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote fork {fork_remote_name!r} using branch {branch_name!r}, "
                f"the error is:\n{ex}"
            )
            raise PackitException(msg)

    def create_pull(
        self, pr_title: str, pr_description: str, source_branch: str, target_branch: str
    ) -> PullRequest:
        """
        Create dist-git pull request using the requested branches
        """
        logger.debug(
            "About to create dist-git pull request "
            f"from {source_branch!r} to {target_branch!r}."
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
    def upstream_archive_name(self) -> str:
        """
        :return: name of the archive, e.g. sen-0.6.1.tar.gz
        """
        with self.specfile.sources() as sources:
            source = next(s for s in sources if s.number == 0)
            archive_name = source.expanded_filename
        logger.debug(f"Upstream archive name: {archive_name}")
        return archive_name

    def download_upstream_archive(self) -> Path:
        """
        Fetch archive for the current upstream release defined in dist-git's spec

        :return: path to the archive
        """
        logger.info(f"Downloading archive: {self.upstream_archive_name}")
        with cwd(self.local_project.working_dir):
            self.download_remote_sources(self.config.pkg_tool)
        archive = self.absolute_source_dir / self.upstream_archive_name
        if not archive.exists():
            raise PackitException(
                "Upstream archive was not downloaded. Check that {} exists in dist-git.".format(
                    self.upstream_archive_name
                )
            )
        return archive

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
            tool=pkg_tool or self.config.pkg_tool,
        )
        pkg_tool_.sources()

    def upload_to_lookaside_cache(self, archive: Path, pkg_tool: str = "") -> None:
        """Upload files (archive) to the lookaside cache.

        If the archive is already uploaded, the rpkg tool doesn't do anything.

        Args:
            archive: Path to archive to upload to lookaside cache.
            pkg_tool: Optional, rpkg tool (fedpkg/centpkg) to use to upload.

        Raises:
            PackitException, if the upload fails.
        """
        logger.info("About to upload to lookaside cache.")
        pkg_tool_ = PkgTool(
            fas_username=self.config.fas_user,
            directory=self.local_project.working_dir,
            tool=pkg_tool or self.config.pkg_tool,
        )
        try:
            pkg_tool_.new_sources(sources=archive)
        except Exception as ex:
            logger.error(
                f"'{pkg_tool_.tool} new-sources' failed for the following reason: {ex!r}"
            )
            raise PackitException(ex)

    def is_archive_in_lookaside_cache(self, archive_path: str) -> bool:
        archive_name = os.path.basename(archive_path)
        try:
            res = requests.head(
                f"{self.package_config.dist_git_base_url}lookaside/pkgs/"
                f"{self.package_config.downstream_package_name}/{archive_name}/"
            )
            if res.ok:
                logger.info(
                    f"Archive {archive_name!r} found in lookaside cache (skipping upload)."
                )
                return True
            logger.debug(f"Archive {archive_name!r} not found in the lookaside cache.")
        except requests.exceptions.HTTPError:
            logger.warning(
                f"Error trying to find {archive_name!r} in the lookaside cache."
            )
        return False

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
        """
        pkg_tool = PkgTool(
            fas_username=self.fas_user,
            directory=self.local_project.working_dir,
            tool=self.config.pkg_tool,
        )
        pkg_tool.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

    @staticmethod
    def get_latest_build_in_tag(downstream_package_name, dist_git_branch):
        """Query Koji for the latest build of a package in a tag.

        Args:
            downstream_package_name (str): package name used for the Koji build
            dist_git_branch (str): dist-git branch where to look for the build
        Returns
            The latest known build
        """

        logger.debug(
            "Querying Koji for the latest build "
            f"of package {downstream_package_name!r} "
            f"in dist-git-branch {dist_git_branch!r}"
        )

        # EPEL uses "testing-candidate" instead of "updates-candidate"
        prefix = "testing" if dist_git_branch.startswith("epel") else "updates"
        koji_tag = f"{dist_git_branch}-{prefix}-candidate"
        session = ClientSession(baseurl=KOJI_BASEURL)
        koji_build = session.listTagged(
            tag=koji_tag,
            package=downstream_package_name,
            inherit=True,
            latest=True,
            strict=False,
        )

        if not koji_build:
            raise PackitException(
                f"There is no build for {downstream_package_name!r} "
                f"and koji tag {koji_tag}"
            )
        else:
            koji_build_str = koji_build[0]["nvr"]
            logger.info(
                "Koji build for package "
                f"{downstream_package_name!r} and koji tag {koji_tag}:"
                f"\n{koji_build_str}"
            )

        return koji_build_str

    def create_bodhi_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: str,
        koji_builds: Optional[Sequence[str]] = None,
        bugzilla_ids: Optional[List[int]] = None,
    ):
        logger.debug(
            f"About to create a Bodhi update of type {update_type!r} from {dist_git_branch!r}"
        )

        bodhi_client = get_bodhi_client(
            fas_username=self.config.fas_user,
            fas_password=self.config.fas_password,
            kerberos_realm=self.config.kerberos_realm,
        )
        # only use Kerberos when fas_user and kerberos_realm are set
        if self.config.fas_user and self.config.kerberos_realm:
            bodhi_client.login_with_kerberos()
        # make sure we have the credentials
        bodhi_client.ensure_auth()

        if not koji_builds:
            koji_builds = [
                self.get_latest_build_in_tag(
                    self.package_config.downstream_package_name,
                    dist_git_branch=dist_git_branch,
                )
            ]

        # I was thinking of verifying that the build is valid for a new bodhi update
        # but in the end it's likely a waste of resources since bodhi will tell us
        rendered_note = update_notes.format(version=self.specfile.expanded_version)
        try:
            save_kwargs = {
                "builds": koji_builds,
                "notes": rendered_note,
                "type": update_type,
            }

            if bugzilla_ids:
                save_kwargs["bugs"] = list(map(str, bugzilla_ids))
            try:
                result = bodhi_client.save(**save_kwargs)
            except BodhiClientException as ex:
                logger.debug(
                    f"Bodhi client raised a login error: {ex}. "
                    f"Let's clear the session, csrf token and retry."
                )
                if self.config.fas_user and self.config.kerberos_realm:
                    bodhi_client.login_with_kerberos()
                bodhi_client.ensure_auth()
                result = bodhi_client.save(**save_kwargs)

            logger.debug(f"Bodhi response:\n{result}")
            logger.info(
                f"Bodhi update {result['alias']}:\n"
                f"- {result['url']}\n"
                f"- stable_karma: {result['stable_karma']}\n"
                f"- unstable_karma: {result['unstable_karma']}\n"
                f"- notes:\n{result['notes']}\n"
            )
            if "caveats" in result:
                for cav in result["caveats"]:
                    logger.info(f"- {cav['name']}: {cav['description']}\n")

        except AuthError as ex:
            logger.error(ex)
            raise PackitException(
                f"There is an authentication problem with Bodhi:\n{ex}"
            ) from ex
        except BodhiClientException as ex:
            logger.error(ex)
            raise PackitException(
                f"There is a problem with creating the bodhi update:\n{ex}"
            ) from ex
        return result["alias"]

    def get_allowed_gpg_keys_from_downstream_config(self) -> Optional[List[str]]:
        if self.downstream_config:
            return self.downstream_config.allowed_gpg_keys
        return None
