import logging
import os
import shutil
from typing import Optional, List, Tuple, Sequence

import git
import requests
from rebasehelper.specfile import SpecFile

from ogr.services.pagure import PagureService
from packit.config import Config, PackageConfig
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.utils import FedPKG

logger = logging.getLogger(__name__)


class DistGit:
    """
    A class which interacts with dist-git and pagure-over-dist-git API.

    The logic covers git and pagure interaction, manipulation with content,
    spec files, patches and archives.

    The expectation is that this class interacts with low level APIs (ogr) and
    doesn't hold any workflow; the workflow and feeding input should be done up the stack.

    The class works with a single instance of dist-git, that's the state,
    and methods of this class interact with the local copy.
    """

    def __init__(self, config: Config, package_config: PackageConfig):
        self.config = config
        self.package_config = package_config

        self._local_project = None

        self.github_token = self.config.github_token
        self.pagure_user_token = self.config.pagure_user_token
        self.pagure_package_token = self.config.pagure_package_token
        self.pagure_fork_token = self.config.pagure_fork_token
        self.package_name: Optional[str] = self.package_config.downstream_package_name
        self.fas_user = self.config.fas_user
        self.dist_git_url: Optional[str] = self.package_config.downstream_project_url
        logger.debug(f"Using dist-git repo {self.dist_git_url}")
        self.files_to_sync: List[str] = self.package_config.synced_files
        self.dist_git_namespace: str = self.package_config.dist_git_namespace
        self._specfile = None

    @property
    def local_project(self):
        """ return an instance of LocalProject """
        if self._local_project is None:
            self._local_project = LocalProject(
                git_url=self.dist_git_url,
                namespace=self.dist_git_namespace,
                repo_name=self.package_name,
                path_or_url=self.package_config.downstream_project_url,
                git_service=PagureService(token=self.pagure_user_token),
            )
        return self._local_project

    @property
    def specfile_path(self) -> Optional[str]:
        if self.package_name:
            return os.path.join(
                self.local_project.working_dir, f"{self.package_name}.spec"
            )
        return None

    @property
    def specfile(self):
        if self._specfile is None:
            self._specfile = SpecFile(
                path=self.specfile_path,
                sources_location=self.local_project.working_dir,
                changelog_entry=None,
            )
        return self._specfile

    def create_branch(
        self, branch_name: str, base: str = "HEAD", setup_tracking: bool = False
    ) -> git.Head:
        """
        Create a new git branch in dist-git

        :param branch_name: name of the branch to check out and fetch
        :param base: we base our new branch on this one
        :param setup_tracking: set up remote tracking (exc raised if branch not in remote)
        :return the branch which was just created
        """
        logger.debug(f"About to create a new git branch {branch_name!r} in dist-git")
        # it's not an error if the branch already exists
        origin = self.local_project.git_repo.remote("origin")
        head = self.local_project.git_repo.create_head(branch_name, commit=base)

        if setup_tracking:
            try:
                remote_ref = origin.refs[branch_name]
            except IndexError:
                raise PackitException("Remote origin doesn't have ref %s" % branch_name)
            # this is important to fedpkg: build can't find the tracking branch otherwise
            head.set_tracking_branch(remote_ref)

        return head

    def update_branch(self, branch_name: str):
        """
        Fetch latest commits to the selected branch; tracking needs to be set up

        :param branch_name: name of the branch to check out and fetch
        """
        logger.debug(f"About to update branch {branch_name!r}")
        origin = self.local_project.git_repo.remote("origin")
        origin.fetch()
        try:
            head = self.local_project.git_repo.heads[branch_name]
        except IndexError:
            raise PackitException(f"Branch {branch_name} does not exist")
        try:
            remote_ref = origin.refs[branch_name]
        except IndexError:
            raise PackitException(
                f"Branch {branch_name} does not exist in the origin remote."
            )
        head.set_commit(remote_ref)

    def checkout_branch(self, git_ref: str):
        """
        Perform a `git checkout`

        :param git_ref: ref to check out
        """
        logger.debug(f"About to checkout {git_ref!r}")
        try:
            head = self.local_project.git_repo.heads[git_ref]
        except IndexError:
            raise PackitException(f"Branch {git_ref} does not exist")
        head.checkout()

    def commit(self, title: str, msg: str, prefix: str = "[packit] ") -> None:
        """
        Perform `git add -A` and `git commit`
        """
        logger.debug("About to add all & commit")
        main_msg = f"{prefix}{title}"
        if not self.local_project.git_repo.is_dirty():
            raise PackitException(
                "No changes are present in the dist-git repo: nothing to commit."
            )
        self.local_project.git_repo.git.add("-A")
        self.local_project.git_repo.index.write()
        commit_args = ["-s", "-m", main_msg]
        if msg:
            commit_args += ["-m", msg]
        # TODO: attach git note to every commit created
        # TODO: implement cleaning policy: once the PR is closed (merged/refused), remove the branch
        #       make this configurable so that people know this would happen, don't clean by default
        #       we should likely clean only merged PRs by default
        # TODO: implement signing properly: we need to create a cert for the bot,
        #       distribute it to the container, prepare git config and then we can start signing
        # TODO: make -s configurable
        self.local_project.git_repo.git.commit(*commit_args)

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
            f"About to {'force ' if force else ''}push changes to branch {branch_name} "
            f"of a fork {fork_remote_name} of the dist-git repo"
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
            self.local_project.git_repo.remote(fork_remote_name).push(
                refspec=branch_name, force=force
            )
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote {fork_remote_name} using branch {branch_name}, "
                f"the error is:\n{ex}"
            )
            raise PackitException(msg)

    def create_pull(
        self, pr_title: str, pr_description: str, source_branch: str, target_branch: str
    ) -> None:
        """
        Create dist-git pull request using the requested branches
        """
        logger.debug(
            "About to create dist-git pull request "
            f"from {source_branch} to {target_branch}"
        )
        project = self.local_project.git_project

        if not self.pagure_user_token:
            raise PackitException(
                "Please provide PAGURE_USER_TOKEN as an environment variable."
            )
        if not self.pagure_fork_token:
            raise PackitException(
                "Please provide PAGURE_FORK_TOKEN as an environment variable."
            )

        project.change_token(self.pagure_user_token)
        # This pagure call requires token from the package's FORK
        project_fork = project.get_fork()
        if not project_fork:
            project.fork_create()
            project_fork = project.get_fork()
        project_fork.change_token(self.pagure_fork_token)

        try:
            dist_git_pr = project_fork.pr_create(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
            )
        except Exception as ex:
            logger.error(f"There was an error while creating the PR: {ex!r}")
            raise
        else:
            logger.info(f"PR created: {dist_git_pr.url}")

    @property
    def upstream_archive_name(self) -> str:
        """
        :return: name of the archive, e.g. sen-0.6.1.tar.gz
        """
        archive_name = self.specfile.get_archive()
        logger.debug(f"Upstream archive name is {archive_name!r}")
        return archive_name

    def download_upstream_archive(self) -> str:
        """
        Fetch archive for the current upstream release defined in dist-git's spec

        :return: str, path to the archive
        """
        self.specfile.download_remote_sources()
        archive = os.path.join(
            self.local_project.working_dir, self.upstream_archive_name
        )
        logger.info(f"Downloaded archive: {archive!r}")
        return archive

    def upload_to_lookaside_cache(self, archive_path: str) -> None:
        """
        Upload files (archive) to the lookaside cache.
        """
        # TODO: can we check if the tarball is already uploaded so we don't have ot re-upload?
        logger.info("About to upload to lookaside cache")
        f = FedPKG(self.fas_user, self.local_project.working_dir)
        f.init_ticket()
        try:
            f.new_sources(sources=archive_path)
        except Exception as ex:
            logger.error(
                f"`fedpkg new-sources` failed for some reason. "
                f"Either Fedora kerberos is invalid or there could be network outage."
            )
            raise PackitException(ex)

    def is_archive_in_lookaside_cache(self, archive_path: str) -> bool:
        archive_name = os.path.basename(archive_path)
        try:
            res = requests.head(
                f"https://src.fedoraproject.org/lookaside/pkgs/{self.package_name}/{archive_name}/"
            )
            if res.ok:
                logger.info(
                    f"Archive {archive_name} found in lookaside cache (skipping upload)."
                )
                return True
            logger.debug(f"Archive {archive_name} not found in the lookaside cache.")
        except requests.exceptions.BaseHTTPError:
            logger.warning(
                f"Error trying to find {archive_name} in the lookaside cache."
            )
        return False

    def purge_unused_git_branches(self):
        # TODO: remove branches from merged PRs
        raise NotImplementedError("not implemented yet")

    def sync_files(self, upstream_project: LocalProject) -> None:
        """
        Sync required files from upstream to downstream.
        """
        logger.debug(f"About to sync files {self.files_to_sync}")
        for fi in self.files_to_sync:
            # TODO: fi can be dir
            fi = fi[1:] if fi.startswith("/") else fi
            src = os.path.join(upstream_project.working_dir, fi)
            if os.path.exists(src):
                logger.info(f"Syncing {src}")
                shutil.copy2(src, self.local_project.working_dir)
            else:
                raise PackitException(
                    f"File {fi} is not present in the upstream repository. "
                    f"Upstream ref {upstream_project.git_repo.head} is checked out"
                )

    def add_patches_to_specfile(self, patch_list: List[Tuple[str, str]]) -> None:
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [(patch_name, msg)] if None, the patches will be generated
        """
        logger.debug(f"About to add patches {patch_list} to specfile")
        if not patch_list:
            return
        if not self.specfile_path:
            raise Exception("No specfile")

        with open(file=self.specfile_path, mode="r+") as spec_file:
            last_source_position = None
            line = spec_file.readline()
            while line:
                if line.startswith("Source"):
                    last_source_position = spec_file.tell()
                line = spec_file.readline()

            if not last_source_position:
                raise Exception("Cannot found place for patches in specfile.")

            spec_file.seek(last_source_position)
            rest_of_the_file = spec_file.read()
            spec_file.seek(last_source_position)

            spec_file.write("\n\n# PATCHES FROM SOURCE GIT:\n")
            for i, (patch, msg) in enumerate(patch_list):
                commented_msg = "\n# " + "\n# ".join(msg.split("\n")) + "\n"
                spec_file.write(commented_msg)
                spec_file.write(f"Patch{i + 1:04d}: {patch}\n")

            spec_file.write(rest_of_the_file)

        logger.info(
            f"Patches ({len(patch_list)}) added to the specfile ({self.specfile_path})"
        )
        self.local_project.git_repo.index.write()

    def build(self, scratch: bool = False):
        """
        Perform a `fedpkg build` in the repository

        :param scratch: should the build be a scratch build?
        """
        fpkg = FedPKG(directory=self.local_project.working_dir)
        fpkg.build(scratch=scratch)

    def create_bodhi_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: str,
        koji_builds: Sequence[str] = None,
    ):
        logger.debug(
            f"About to create a Bodhi update of type {update_type} from {dist_git_branch}"
        )
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient, BodhiClientException

        if not self.package_name:
            raise PackitException("Package name is not set.")
        # bodhi will likely prompt for username and password if kerb ticket is not up
        b = BodhiClient()
        if not koji_builds:
            # alternatively we can call something like `koji latest-build rawhide sen`
            builds_d = b.latest_builds(self.package_name)

            builds_str = "\n".join(f" - {b}" for b in builds_d)
            logger.debug(f"Koji builds for package {self.package_name}: \n{builds_str}")

            koji_tag = f"{dist_git_branch}-updates-candidate"
            try:
                koji_builds = [builds_d[koji_tag]]
                koji_builds_str = "\n".join(f" - {b}" for b in koji_builds)
                logger.info(
                    f"Koji builds for package {self.package_name} and koji tag {koji_tag}:"
                    f"\n{koji_builds_str}"
                )
            except KeyError:
                raise PackitException(
                    f"There is no build for {self.package_name} in koji tag {koji_tag}"
                )
        # I was thinking of verifying that the build is valid for a new bodhi update
        # but in the end it's likely a waste of resources since bodhi will tell us
        rendered_note = update_notes.format(version=self.specfile.get_full_version())
        try:
            result = b.save(builds=koji_builds, notes=rendered_note, type=update_type)
            logger.debug(f"Bodhi response:\n{result}")
            logger.info(
                f"Bodhi update {result['alias']}:\n"
                f"- {result['url']}\n"
                f"- stable_karma: {result['stable_karma']}\n"
                f"- unstable_karma: {result['unstable_karma']}"
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
