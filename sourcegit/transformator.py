from __future__ import annotations

import logging
import os
import shutil
import tempfile
# decorator for cached properties, in python >=3.8 use cached_property
from distutils.dir_util import copy_tree
from functools import lru_cache
from typing import Optional, List, Tuple

import git

from ogr.abstract import GitProject
from sourcegit.config import PackageConfig
from sourcegit.constants import DG_PR_COMMENT_KEY_SG_PR, DG_PR_COMMENT_KEY_SG_COMMIT
from sourcegit.downstream_checks import get_check_by_name
from sourcegit.utils import get_rev_list_kwargs, FedPKG, run_command
from sourcegit.watcher import SourceGitCheckHelper

logger = logging.getLogger(__name__)


class Transformator:
    """
    Describes relation between sourcegit and distgit repository.

    Allows multiple actions and transformation of the repos.
    """

    def __init__(
            self,
            package_config: PackageConfig,
            branch: str = None,
            version: str = None,
            dest_dir: str = None,
            fas_username: str = None,
            url: str = None,
            repo: git.Repo = None,
    ) -> None:

        self.package_config = package_config
        self._repo = repo
        if repo:
            self._branch = branch or repo.active_branch
            self.repo_url = url or list(repo.remote().urls)[0]
        else:
            self._branch = branch
            self.repo_url = url

        self._version = version
        self._temp_dir: Optional[str] = None
        self.rev_list_option_args = get_rev_list_kwargs(
            self.package_config.metadata.get("rev_list_option", ["first_parent"])
        )

        self.fas_username = fas_username

        self.upstream_name = self.package_config.metadata["upstream_name"]
        self.package_name = (
                self.package_config.metadata["package_name"] or self.upstream_name
        )
        self.dest_dir = dest_dir or tempfile.mkdtemp()
        self.dist_git_url = self.package_config.metadata["dist_git_url"]

    @property
    def branch(self) -> str:
        """
        Source branch in the source-git repo.
        """
        if not self._branch:
            self._branch = f"upstream-{self.version}"
        return self._branch

    @property
    def repo(self) -> git.Repo:
        """
        Repository used as a source.
        """
        if not self._repo:
            repo_path = os.path.join(self.temp_dir, self.upstream_name)
            logger.info(
                f"Cloning source-git repo: {self.repo_url} ({self.branch})-> {repo_path}"
            )
            self._repo = git.repo.Repo.clone_from(
                url=self.repo_url, to_path=repo_path, branch=self.branch, tags=True
            )
        return self._repo

    @property
    @lru_cache()
    def dist_git_repo(self) -> git.Repo:
        """
        Clone the dist_git repository to the destination dir and return git.Repo instance

        :return: git.Repo instance
        """
        return self.clone_dist_git_repo()

    @property
    def temp_dir(self) -> str:
        """
        Dir used for storing temp. content. e.g. source-git repo.
        """
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp()
            logger.debug(f"Creating temp dir: {self._temp_dir}")
        return self._temp_dir

    @property
    @lru_cache()
    def specfile_path(self) -> str:
        return os.path.join(
            self.repo.working_tree_dir, self.package_config.specfile_path
        )

    @property
    @lru_cache()
    def archive(self) -> str:
        """
        Path of the archive generated from the source-git.
        If not exists, the archive will be created in the destination directory.
        """
        archive = self.create_archive()
        return archive

    @property
    @lru_cache()
    def version(self) -> str:
        return self._version or self.version_from_specfile

    @property
    @lru_cache()
    def version_from_specfile(self) -> str:
        """
        Version extracted from the specfile.
        """
        version_raw = run_command(
            cmd=[
                "rpmspec",
                "-q",
                "--qf",
                "'%{version}\\n'",
                "--srpm",
                self.specfile_path,
            ],
            output=True,
            fail=True,
        )
        version = version_raw.strip("'\\\n")
        return version

    @property
    @lru_cache()
    def fedpkg(self) -> FedPKG:
        """
        Instance of the FedPKG class (wrapper on top of the fedpkg command.)
        """
        return FedPKG(
            fas_username=self.fas_username,
            repo_path=self.dist_git_url,
            directory=self.dest_dir,
        )

    def clean(self) -> None:
        """
        Clean te temporary dir.
        """
        logger.debug(f"Cleaning: {self.temp_dir}")
        shutil.rmtree(self.temp_dir)
        self._temp_dir = None

    def create_archive(
            self, path: str = None, name="{project}-{version}.tar.gz"
    ) -> str:
        """
        Create archive from the provided git repo. The archive needs to be able to be used to build
        the project using rpmbuild command. The expectation is that the directory within the archive
        should be named {project}-{version}.

        :return: str, path to the archive
        """
        archive_name = name.format(project=self.upstream_name, version=self.version)
        archive_path = path or os.path.join(self.dest_dir, archive_name)

        self.add_exclude_redhat_to_gitattributes()

        with open(archive_path, "wb") as fp:
            self.repo.archive(
                fp, prefix=f"./{self.upstream_name}/", worktree_attributes=True
            )

        logger.info(f"Archive created: {archive_path}")
        return archive_path

    def add_exclude_redhat_to_gitattributes(self) -> None:
        """
        Add a line to .gitattributes to export-ignore redhat dir.
        TODO: We need to use upstream release archive directly
        """
        logger.debug("Adding 'redhat/ export-ignore' to .gitattributes")
        gitattributes_path = os.path.join(self.repo.working_tree_dir, ".gitattributes")
        with open(gitattributes_path, "a") as gitattributes_file:
            for file in self.package_config.synced_files:
                file_in_working_dir = os.path.join(self.repo.working_tree_dir, file)
                if os.path.isdir(file_in_working_dir):
                    gitattributes_file.writelines([f"{file}/ export-ignore\n"])
                elif os.path.isfile(file_in_working_dir):
                    gitattributes_file.writelines([f"{file} export-ignore\n"])

    @lru_cache()
    def create_srpm(self) -> None:
        logger.debug("Start creating og the SRPM.")
        archive = self.create_archive()
        logger.debug(f"Using archive: {archive}")

        spec_dir = os.path.dirname(self.specfile_path)
        run_command(
            cmd=[
                "rpmbuild",
                "-bs",
                f"{self.specfile_path}",
                "--define",
                f"_sourcedir {spec_dir}",
                "--define",
                f"_specdir {spec_dir}",
                "--define",
                f"_buildir {spec_dir}",
                "--define",
                f"_srcrpmdir {self.dest_dir}",
                "--define",
                f"_rpmdir {spec_dir}",
            ],
            fail=True,
        )

    @lru_cache()
    def get_commits_to_upstream(
            self, upstream: str, add_usptream_head_commit=False
    ) -> List[git.Commit]:
        """
        Return the list of commits from current branch to upstream rev/tag.

        :param upstream: str -- git branch or tag
        :return: list of commits (last commit on the current branch.).
        """

        if upstream in self.repo.tags:
            upstream_ref = upstream
        else:
            upstream_ref = f"origin/{upstream}"
            if upstream_ref not in self.repo.refs:
                raise Exception(
                    f"Upstream {upstream_ref} branch nor {upstream} tag not found."
                )

        commits = list(
            self.repo.iter_commits(
                rev=f"{upstream_ref}..{self.branch}",
                reverse=True,
                **self.rev_list_option_args,
            )
        )
        if add_usptream_head_commit:
            commits.insert(0, self.repo.refs[f"{upstream_ref}"].commit)

        logger.debug(f"Delta ({upstream_ref}..{self.branch}): {len(commits)}")
        return commits

    @lru_cache()
    def clone_dist_git_repo(self, new_branch_to_checkout: str = None) -> git.Repo:
        """
        Clone the dist_git repository to the destination dir and return git.Repo instance

        :return: git.Repo instance
        """
        # TODO: optimize cloning: single branch and last 3 commits?
        if os.path.isdir(os.path.join(self.dest_dir, ".git")):
            logger.info(f"Dist-git already present: {self.dest_dir}")
            return git.repo.Repo(self.dest_dir)

        logger.info(f"Cloning dist-git repo: {self.dist_git_url} -> {self.dest_dir}")
        repo = git.repo.Repo.clone_from(
            url=self.dist_git_url, to_path=self.dest_dir, tags=True
        )

        if new_branch_to_checkout:
            new_branch = repo.create_head(new_branch_to_checkout)
            new_branch.checkout()
        return repo

    def create_patches(self, upstream: str = None) -> List[Tuple[str, str]]:
        """
        Create patches from downstream commits.

        :param upstream: str -- git branch or tag
        :return: [(patch_name, msg)] list of created patches (tuple of the file name and commit msg)
        """

        upstream = upstream or self.version_from_specfile
        commits = self.get_commits_to_upstream(upstream, add_usptream_head_commit=True)
        patch_list = []
        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            patch_name = f"{i + 1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(self.dest_dir, patch_name)
            patch_msg = f"{commit.summary}\nAuthor: {commit.author.name} <{commit.author.email}>"

            logger.debug(f"PATCH: {patch_name}\n{patch_msg}")
            diff = run_command(
                cmd=[
                    "git",
                    "diff",
                    "--patch",
                    parent.hexsha,
                    commit.hexsha,
                    "--",
                    ".",
                    '":(exclude)redhat"',
                ],
                cwd=self.repo.working_tree_dir,
                output=True,
            )

            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)
            patch_list.append((patch_name, patch_msg))

        return patch_list

    def add_patches_to_specfile(self, patch_list: List[Tuple[str, str]] = None) -> None:
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [(patch_name, msg)] if None, the patches will be generated
        """
        if patch_list is None:
            patch_list = self.create_patches()

        specfile_path = os.path.join(self.dest_dir, f"{self.package_name}.spec")

        with open(file=specfile_path, mode="r+") as spec_file:
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
            f"Patches ({len(patch_list)}) added to the specfile ({specfile_path})"
        )
        self.repo.index.write()

    def copy_synced_content_to_dest_dir(self, synced_files: List[str]) -> None:
        """
        Copy files from source-git to destination directory.
        """
        for file in synced_files:
            file_in_working_dir = os.path.join(self.repo.working_tree_dir, file)
            logger.debug(f"Copying '{file_in_working_dir}' to distgit.")
            if os.path.isdir(file_in_working_dir):
                copy_tree(src=file_in_working_dir, dst=self.dest_dir)
            elif os.path.isfile(file_in_working_dir):
                shutil.copy2(file_in_working_dir, os.path.join(self.dest_dir, file))

    def upload_archive_to_lookaside_cache(self, keytab: str) -> None:
        """
        Upload the archive to the lookaside cache using fedpkg.
        (If not exists, the archive will be created.)
        """
        logger.info("Uploading the archive to lookaside cache.")
        self.fedpkg.init_ticket(keytab)
        self.fedpkg.new_sources(sources=self.archive, fail=False)

    def commit_distgit(self, title: str, msg: str) -> None:
        main_msg = f"[source-git] {title}"
        self.dist_git_repo.git.add("-A")
        self.dist_git_repo.index.write()
        # TODO: implement signing properly: we need to create a cert for the bot, distribute it to the container,
        #       prepare git config and then we can start signing
        # TODO: make -s configurable
        self.dist_git_repo.git.commit("-s", "-m", main_msg, "-m", msg)

    def reset_checks(
            self, full_name: str, pr_id: int, github_token: str, pagure_user_token: str
    ) -> None:
        """
        Before syncing a new change downstream, we need to reset status of checks
        for all the configured tests
        and wait for testing systems to get us the new ones.
        """
        sg = SourceGitCheckHelper(github_token, pagure_user_token)
        for check_dict in self.package_config.metadata["checks"]:
            check = get_check_by_name(check_dict["name"])
            sg.set_init_check(full_name, pr_id, check)

    def update_or_create_dist_git_pr(
            self,
            project: GitProject,
            pr_id: int,
            pr_url: str,
            top_commit: str,
            title: str,
            source_ref: str,
            pagure_fork_token: str,
            pagure_package_token: str,
    ) -> None:
        # Sadly, pagure does not support editing initial comments of a PR via the API
        # https://pagure.io/pagure/issue/4111
        # Short-term solution: keep adding comments
        # and get updated info about sg PR ID and commit desc
        for pr in project.get_pr_list():

            sg_pr_id_match = project.search_in_pr(
                pr_id=pr.id,
                filter_regex=DG_PR_COMMENT_KEY_SG_PR + r":\s*(\d+)",
                reverse=True,
                description=True,
            )
            if not sg_pr_id_match:
                logger.debug(f"No automation comment found in dist-git PR: {pr.id}.")
                continue

            sg_pr_id = sg_pr_id_match[1]
            if sg_pr_id_match[1] != str(pr_id):
                logger.debug(
                    f"Dist-git PR `{pr.id}` does not match " f"source-git PR `{pr_id}`."
                )
                continue

            commit_match = project.search_in_pr(
                pr_id=pr.id,
                filter_regex=DG_PR_COMMENT_KEY_SG_COMMIT + r":\s*(\d+)",
                reverse=True,
                description=True,
            )
            if not commit_match:
                logger.debug(
                    f"Dist-git PR `{pr.id}` does not contain top-commit of the "
                    f"source-git PR `{pr_id}`."
                )
                continue

            logger.debug(f"Adding a new comment with update to existing PR.")
            msg = (
                f"New changes were pushed to the upstream pull request\n\n"
                f"[{DG_PR_COMMENT_KEY_SG_PR}: {pr_id}]({pr_url})\n"
                f"{DG_PR_COMMENT_KEY_SG_COMMIT}: {top_commit}"
            )
            # FIXME: consider storing the data above as a git note of the top commit
            project.change_token(pagure_package_token)
            project.pr_comment(pr.id, msg)
            logger.info("new comment added on PR %s", sg_pr_id)
            break
        else:
            logger.debug(f"Matching dist-git PR not found => creating a new one.")
            msg = (
                f"This pull request contains changes from upstream "
                f"and is meant to integrate them into Fedora\n\n"
                f"[{DG_PR_COMMENT_KEY_SG_PR}: {pr_id}]({pr_url})\n"
                f"{DG_PR_COMMENT_KEY_SG_COMMIT}: {top_commit}"
            )
            # This pagure call requires token from the package's FORK
            project_fork = project.get_fork()
            project_fork.change_token(pagure_fork_token)
            dist_git_pr_id = project_fork.pr_create(
                title=f"[source-git] {title}",
                body=msg,
                source_branch=source_ref,
                target_branch="master",
            ).id
            logger.info(f"PR created: {dist_git_pr_id}")

    def push_to_distgit_fork(self, project_fork, branch_name):
        if "origin-fork" not in [remote.name for remote in self.dist_git_repo.remotes]:
            self.dist_git_repo.create_remote(
                name="origin-fork", url=project_fork.get_git_urls()["ssh"]
            )

        # I suggest to comment this one while testing when the push is not needed
        self.dist_git_repo.remote("origin-fork").push(
            refspec=branch_name, force=branch_name in project_fork.get_branches()
        )

    def __enter__(self) -> Transformator:
        return self

    def __exit__(self, *args) -> None:
        self.clean()
