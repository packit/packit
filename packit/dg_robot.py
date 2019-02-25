import os
import shutil
import tempfile
from typing import List

from ogr.services.pagure import PagureService
from rebasehelper.specfile import SpecFile

from packit.config import Config
from packit.local_project import LocalProject
from packit.sync import logger
from packit.utils import FedPKG


# TODO: create a DistGit class
class DistGitRobot:
    """
    A class which interacts with dist-git and pagure-over-dist-git API.

    The logic covers git and pagure interaction, manipulation with content, spec files, patches and archives

    The expectation is that this class interacts with low level APIs (ogr) and doesn't hold any workflow; the
    workflow and feeding input should be done up the stack

    The expectation is that we work with a single instance of dist-git, that's the state, and methods of this class
    interact with the local copy
    """
    def __init__(
            self,
            github_token: str,
            pagure_user_token: str,
            pagure_package_token: str,
            pagure_fork_token: str,
            package_name: str,
            fas_user: str,
            dist_git_url: str,
            dist_git_namespace: str = "rpms",
            dist_git_path: str = None,
            upstream_project_url: str = ".",  # can be URL or path
    ) -> None:
        self.github_token = github_token
        self.pagure_user_token = pagure_user_token
        self.pagure_package_token = pagure_package_token
        self.pagure_fork_token = pagure_fork_token

        self.package_name = package_name
        self.fas_user = fas_user
        self.dist_git_url = dist_git_url
        self.dist_git_namespace = dist_git_namespace
        self.dist_git_path = dist_git_path
        self.upstream_project_url = upstream_project_url

        self._distgit = None
        self._upstream_project = None
        self._package_config = None
        self._distgit_spec = None
        self._upstream_spec = None

    @property
    def distgit_spec_path(self):
        return os.path.join(
            self.distgit.working_dir,
            f"{self.package_name}.spec"
        )

    @property
    def upstream_spec_path(self):
        return os.path.join(
            self.upstream.working_dir,
            f"{self.package_name}.spec"
        )

    @property
    def upstream(self):
        """  """
        if self._upstream_project is None:
            self._upstream_project = LocalProject(
                working_dir=self.upstream_project_url
            )
        return self._upstream_project

    @property
    def distgit_specfile(self):
        if self._distgit_spec is None:
            self._distgit_spec = SpecFile(
                path=self.distgit_spec_path,
                sources_location=self.distgit.working_dir,
                changelog_entry=None,
            )
        return self._distgit_spec

    @property
    def upstream_specfile(self):
        if self._upstream_spec is None:
            self._upstream_spec = SpecFile(
                path=self.upstream_spec_path,
                sources_location=self.upstream.working_dir,
                changelog_entry=None,
            )
        return self._upstream_spec

    @property
    def distgit(self):
        """  """
        if self._distgit is None:
            self._distgit = LocalProject(
                git_url=self.dist_git_url,
                namespace=self.dist_git_namespace,
                repo_name=self.package_name,
                working_dir=self.dist_git_path,
                git_service=PagureService(token=self.pagure_user_token),

            )
        return self._distgit

    def download_upstream_archive(self) -> str:
        """
        Fetch archive for the current upstream release defined in dist-git's spec

        :return: str, path to the archive
        """
        self.distgit_specfile.download_remote_sources()
        archive_name = self.distgit_specfile.get_archive()
        archive = os.path.join(self.distgit.working_dir, archive_name)
        logger.info("downloaded archive: %s", archive)
        return archive

    def upload_to_lookaside_cache(self, archive_path: str) -> None:
        """
        upload files (archive) to the lookaside cache
        """
        f = FedPKG(self.fas_user, self.distgit.working_dir)
        f.init_ticket()
        f.new_sources(sources=archive_path)

    def sync_files(self, files_to_sync: List[str]) -> None:
        """
        sync required files from upstream to downstream
        """
        for fi in files_to_sync:
            fi = fi[1:] if fi.startswith("/") else fi
            src = os.path.join(self.upstream.working_dir, fi)
            shutil.copy2(src, self.distgit.working_dir)

    def create_branch_distgit(self, branch_nane: str):
        # fetch and reset --hard master?
        # what if the branch already exists?
        self.distgit.git_repo.create_head(branch_nane)

    def checkout_branch_distgit(self, git_ref: str):
        self.distgit.git_repo.heads[git_ref].checkout()

    def commit_distgit(self, title: str, msg: str) -> None:
        main_msg = f"[packit] {title}"
        self.distgit.git_repo.git.add("-A")
        self.distgit.git_repo.index.write()
        # TODO: attach git note to every commit created
        # TODO: implement cleaning policy: once the PR is closed (merged/refused), remove the branch
        #       make this configurable so that people know this would happen, don't clean by default
        #       we should likely clean only merged PRs by default
        # TODO: implement signing properly: we need to create a cert for the bot, distribute it to the container,
        #       prepare git config and then we can start signing
        # TODO: make -s configurable
        self.distgit.git_repo.git.commit("-s", "-m", main_msg, "-m", msg)

    def push_distgit_fork(self, branch_name: str, fork_remote_name: str = "fork"):
        """
        push changes to the dist-git repo; they need to be committed!

        :param branch_name: the branch where we push
        :param fork_remote_name: local name of the remote where we push to
        """
        if fork_remote_name not in [
            remote.name for remote in self.distgit.git_repo.remotes
        ]:
            fork_urls = self.distgit.git_project.get_fork().get_git_urls()
            self.distgit.git_repo.create_remote(
                name=fork_remote_name, url=fork_urls["ssh"]
            )

        # I suggest to comment this one while testing when the push is not needed
        # TODO: create dry-run ^
        fork_branches = self.distgit.git_project.get_fork().get_branches()
        self.distgit.git_repo.remote(fork_remote_name).push(
            refspec=branch_name, force=branch_name in fork_branches
        )

    def create_pull(
            self,
            pr_title: str,
            pr_description: str,
            source_branch: str,
            target_branch: str,
    ) -> None:
        """
        use the content of the dist-git repo and create a PR
        :return:
        """
        project = self.distgit.git_project

        project.change_token(self.pagure_user_token)
        # This pagure call requires token from the package's FORK
        project_fork = project.get_fork()
        if not project_fork:
            project.fork_create()
            project_fork = project.get_fork()
        project_fork.change_token(self.pagure_fork_token)

        dist_git_pr_id = project_fork.pr_create(
            title=pr_title,
            body=pr_description,
            source_branch=source_branch,
            target_branch=target_branch,
        ).id
        logger.info(f"PR created: {dist_git_pr_id}")

    def purge_unused_git_branches(self):
        # TODO: remove branches from merged PRs
        raise NotImplementedError("not implemented yet")


class PackitDistGitRobot(DistGitRobot):
    """ packit specific code which fills in the data """
    def __init__(self, config: Config, dist_git_path: str = None):
        self.config = config
        self._package_config = None

        super().__init__(
            github_token=self.config.github_token,
            pagure_user_token=self.config.pagure_user_token,
            pagure_package_token=self.config.pagure_package_token,
            pagure_fork_token=self.config.pagure_fork_token,
            package_name=self.config.package_config.metadata['package_name'],
            fas_user=self.config.fas_user,
            dist_git_url=self.config.package_config.metadata['dist_git_url'],
            dist_git_path=dist_git_path,
        )

    def sync_files(self):
        return super().sync_files(self.config.package_config.synced_files)
