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

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Sequence, List

import cccolutils
import git
import requests
from ogr.abstract import PullRequest

from packit.base_git import PackitRepositoryBase
from packit.config import (
    Config,
    PackageConfig,
    SyncFilesConfig,
    get_local_package_config,
)
from packit.config.common_package_config import CommonPackageConfig
from packit.exceptions import PackitException, PackitConfigException
from packit.fedpkg import FedPKG
from packit.local_project import LocalProject
from packit.utils import cwd

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

    def __init__(
        self,
        config: Config,
        package_config: CommonPackageConfig,
        local_project: LocalProject = None,
    ):
        super().__init__(config=config, package_config=package_config)

        self._local_project = local_project

        self.fas_user = self.config.fas_user
        self.files_to_sync: Optional[SyncFilesConfig] = self.package_config.synced_files
        self._downstream_config: Optional[PackageConfig] = None

    @property
    def local_project(self):
        """ return an instance of LocalProject """
        if self._local_project is None:
            dist_git_project = self.config.get_project(
                url=self.package_config.dist_git_package_url
            )

            if self.package_config.dist_git_clone_path:
                self._local_project = LocalProject(
                    working_dir=self.package_config.dist_git_clone_path,
                    git_url=self.package_config.dist_git_package_url,
                    namespace=self.package_config.dist_git_namespace,
                    repo_name=self.package_config.downstream_package_name,
                    git_project=dist_git_project,
                )
            else:
                tmpdir = tempfile.mkdtemp(prefix="packit-dist-git")
                f = FedPKG(fas_username=self.fas_user, directory=tmpdir)
                f.clone(
                    self.package_config.downstream_package_name,
                    tmpdir,
                    anonymous=not cccolutils.has_creds(),
                )
                self._local_project = LocalProject(
                    working_dir=tmpdir,
                    git_url=self.package_config.dist_git_package_url,
                    namespace=self.package_config.dist_git_namespace,
                    repo_name=self.package_config.downstream_package_name,
                    git_project=dist_git_project,
                )
                self._local_project.working_dir_temporary = True
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

    def get_absolute_specfile_path(self) -> Path:
        """ provide the path, don't check it """
        return (
            Path(self.local_project.working_dir)
            / f"{self.package_config.downstream_package_name}.spec"
        )

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
            dist_git_pr = project_fork.pr_create(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
            )
        except Exception as ex:
            logger.error(f"There was an error while creating the PR: {ex!r}")
            if "Pull-Request have been deactivated" in str(ex):
                logger.info("See https://github.com/packit-service/packit/issues/328")
            raise
        else:
            logger.info(f"PR created: {dist_git_pr.url}")
            return dist_git_pr

    @property
    def upstream_archive_name(self) -> str:
        """
        :return: name of the archive, e.g. sen-0.6.1.tar.gz
        """
        archive_name = self.specfile.get_archive()
        logger.debug(f"Upstream archive name: {archive_name}")
        return archive_name

    def download_upstream_archive(self) -> Path:
        """
        Fetch archive for the current upstream release defined in dist-git's spec

        :return: str, path to the archive
        """
        with cwd(self.local_project.working_dir):
            self.specfile.download_remote_sources()
        archive = self.absolute_specfile_dir / self.upstream_archive_name
        if not archive.exists():
            raise PackitException(
                "Upstream archive was not downloaded, something is wrong."
            )
        logger.info(f"Downloaded archive: {archive}")
        return archive

    def upload_to_lookaside_cache(self, archive_path: str) -> None:
        """
        Upload files (archive) to the lookaside cache.
        """
        # TODO: can we check if the tarball is already uploaded so we don't have ot re-upload?
        logger.info("About to upload to lookaside cache.")
        f = FedPKG(
            fas_username=self.config.fas_user, directory=self.local_project.working_dir
        )
        try:
            f.new_sources(sources=archive_path)
        except Exception as ex:
            logger.error(
                f"The 'fedpkg new-sources' command failed for the following reason: {ex!r}"
            )
            raise PackitException(ex)

    def is_archive_in_lookaside_cache(self, archive_path: str) -> bool:
        archive_name = os.path.basename(archive_path)
        try:
            res = requests.head(
                "https://src.fedoraproject.org/lookaside/pkgs/"
                f"{self.package_config.downstream_package_name}/{archive_name}/"
            )
            if res.ok:
                logger.info(
                    f"Archive {archive_name!r} found in lookaside cache (skipping upload)."
                )
                return True
            logger.debug(f"Archive {archive_name!r} not found in the lookaside cache.")
        except requests.exceptions.BaseHTTPError:
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
        fpkg = FedPKG(
            fas_username=self.fas_user, directory=self.local_project.working_dir
        )
        fpkg.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

    def create_bodhi_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: str,
        koji_builds: Sequence[str] = None,
    ):
        logger.debug(
            f"About to create a Bodhi update of type {update_type!r} from {dist_git_branch!r}"
        )
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient, BodhiClientException

        # bodhi will likely prompt for username and password if kerb ticket is not up
        b = BodhiClient()
        if not koji_builds:
            # alternatively we can call something like `koji latest-build rawhide sen`
            builds_d = b.latest_builds(self.package_config.downstream_package_name)

            builds_str = "\n".join(f" - {b}" for b in builds_d)
            logger.debug(
                "Koji builds for package "
                f"{self.package_config.downstream_package_name!r}: \n{builds_str}"
            )

            koji_tag = f"{dist_git_branch}-updates-candidate"
            try:
                koji_builds = [builds_d[koji_tag]]
                koji_builds_str = "\n".join(f" - {b}" for b in koji_builds)
                logger.info(
                    "Koji builds for package "
                    f"{self.package_config.downstream_package_name!r} and koji tag {koji_tag}:"
                    f"\n{koji_builds_str}"
                )
            except KeyError:
                raise PackitException(
                    f"There is no build for {self.package_config.downstream_package_name!r} "
                    f"in koji tag {koji_tag}"
                )
        # I was thinking of verifying that the build is valid for a new bodhi update
        # but in the end it's likely a waste of resources since bodhi will tell us
        rendered_note = update_notes.format(version=self.specfile.get_version())
        try:
            result = b.save(builds=koji_builds, notes=rendered_note, type=update_type)
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

        except BodhiClientException as ex:
            logger.error(ex)
            raise PackitException(
                f"There is a problem with creating the bodhi update:\n{ex}"
            )
        return result["alias"]

    def get_allowed_gpg_keys_from_downstream_config(self) -> Optional[List[str]]:
        if self.downstream_config:
            return self.downstream_config.allowed_gpg_keys
        return None
