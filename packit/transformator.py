from __future__ import annotations

import logging
import os
import shutil
from distutils.dir_util import copy_tree
from functools import lru_cache
from typing import List, Tuple

import git
from rebasehelper.specfile import SpecFile
from rebasehelper.versioneer import versioneers_runner

from ogr.abstract import GitProject
from packit.config import PackageConfig
from packit.constants import DG_PR_COMMENT_KEY_SG_PR, DG_PR_COMMENT_KEY_SG_COMMIT
from packit.downstream_checks import get_check_by_name
from packit.local_project import LocalProject
from packit.utils import get_rev_list_kwargs, FedPKG, run_command
from packit.watcher import SourceGitCheckHelper

logger = logging.getLogger(__name__)


# TODO: refactor this class, it's too complex
class Transformator:
    """
    Describes a relation between a source-git and a dist-git repository.

    Allows multiple actions and transformation operations of the repos.
    """

    def __init__(
        self,
        package_config: PackageConfig,
        sourcegit: LocalProject,
        distgit: LocalProject,
        version: str = None,
        fas_username: str = None,
    ) -> None:

        self.package_config = package_config
        self.sourcegit = sourcegit
        self.distgit = distgit

        self._version = version
        self.rev_list_option_args = get_rev_list_kwargs(
            self.package_config.metadata.get("rev_list_option", ["first_parent"])
        )

        self.fas_username = fas_username

        self.upstream_name = self.package_config.metadata["upstream_name"]
        self.package_name = (
            self.package_config.metadata["package_name"] or self.upstream_name
        )

        self._archive = None

    @property
    @lru_cache()
    def source_specfile_path(self) -> str:
        return os.path.join(
            self.sourcegit.working_dir, self.package_config.specfile_path
        )

    @property
    @lru_cache()
    def dist_specfile_path(self) -> str:
        return os.path.join(self.distgit.working_dir, f"{self.package_name}.spec")

    @property
    @lru_cache()
    def archive(self) -> str:
        """
        Path of the archive generated from the source-git.
        If not exists, the archive will be created in the destination directory.
        """
        if not self._archive:
            self._archive = self.download_upstream_archive()
        return self._archive

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
                self.source_specfile_path,
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
            repo_path=self.distgit.git_url,
            directory=self.distgit.working_dir,
        )

    @property
    def distgit_spec(self) -> SpecFile:
        return SpecFile(
            path=self.dist_specfile_path,
            sources_location=self.distgit.working_dir,
            changelog_entry=None,
        )

    def clean(self) -> None:
        """
        Clean te temporary dir.
        """
        pass

    def save_archive(
        self, path: str = None, release: str = None, name="{project}-{version}.tar.gz"
    ):
        """
        Saves the release archive.
        """

        if release:
            release = self.sourcegit.git_project.get_release(release)
        else:
            release = self.sourcegit.git_project.get_releases()[-1]

        archive_name = name.format(project=self.upstream_name, version=self.version)
        archive_path = path or os.path.join(self.distgit.working_dir, archive_name)
        release.save_archive(path=archive_path)

    def download_upstream_archive(self):
        self.distgit_spec.download_remote_sources()
        archive_name = self.distgit_spec.get_archive()
        self._archive = os.path.join(self.distgit.working_dir, archive_name)
        logger.info(f"Downloaded archive: {self._archive}")

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
        archive_path = path or os.path.join(self.distgit.working_dir, archive_name)

        self.add_exclude_redhat_to_gitattributes()

        with open(archive_path, "wb") as fp:
            self.sourcegit.git_repo.archive(
                fp,
                prefix=f"./{self.upstream_name}-{self.version}/",
                worktree_attributes=True,
            )

        logger.info(f"Archive created: {archive_path}")
        return archive_path

    def add_exclude_redhat_to_gitattributes(self) -> None:
        """
        Add a line to .gitattributes to export-ignore redhat dir.
        TODO: We need to use upstream release archive directly
        """
        logger.debug("Adding 'redhat/ export-ignore' to .gitattributes")
        gitattributes_path = os.path.join(self.sourcegit.working_dir, ".gitattributes")
        with open(gitattributes_path, "a") as gitattributes_file:
            for file in self.package_config.synced_files:
                file_in_working_dir = os.path.join(self.sourcegit.working_dir, file)
                if os.path.isdir(file_in_working_dir):
                    gitattributes_file.writelines([f"{file}/ export-ignore\n"])
                elif os.path.isfile(file_in_working_dir):
                    gitattributes_file.writelines([f"{file} export-ignore\n"])

    @lru_cache()
    def create_srpm(self) -> str:
        logger.debug("Start creating of the SRPM.")
        if not self.archive:
            logger.error("No source archive found.")
            raise Exception("No source archive found.")
        logger.debug(f"Using archive: {self.archive}")

        output = run_command(
            cmd=[
                "rpmbuild",
                "-bs",
                f"{self.dist_specfile_path}",
                "--define",
                f"_sourcedir {self.distgit.working_dir}",
                "--define",
                f"_specdir {self.distgit.working_dir}",
                "--define",
                f"_buildir {self.distgit.working_dir}",
                "--define",
                f"_srcrpmdir {self.distgit.working_dir}",
                "--define",
                f"_rpmdir {self.distgit.working_dir}",
            ],
            fail=True,
            output=True,
        )
        specfile_name = output.split(':')[1].rstrip()
        logger.info(f"Specfile created: {specfile_name}")
        return specfile_name

    @lru_cache()
    def get_commits_to_upstream(
        self, upstream: str, add_usptream_head_commit=False
    ) -> List[git.Commit]:
        """
        Return the list of commits from current branch to upstream rev/tag.

        :param upstream: str -- git branch or tag
        :return: list of commits (last commit on the current branch.).
        """

        if upstream in self.sourcegit.git_repo.tags:
            upstream_ref = upstream
        else:
            upstream_ref = f"origin/{upstream}"
            if upstream_ref not in self.sourcegit.git_repo.refs:
                raise Exception(
                    f"Upstream {upstream_ref} branch nor {upstream} tag not found."
                )

        commits = list(
            self.sourcegit.git_repo.iter_commits(
                rev=f"{upstream_ref}..{self.sourcegit._branch}",
                reverse=True,
                **self.rev_list_option_args,
            )
        )
        if add_usptream_head_commit:
            commits.insert(0, self.sourcegit.git_repo.refs[f"{upstream_ref}"].commit)

        logger.debug(
            f"Delta ({upstream_ref}..{self.sourcegit._branch}): {len(commits)}"
        )
        return commits

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
            patch_path = os.path.join(self.distgit.working_dir, patch_name)
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
                cwd=self.sourcegit.working_dir,
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

        if not patch_list:
            return

        specfile_path = os.path.join(
            self.distgit.working_dir, f"{self.package_name}.spec"
        )

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
        self.sourcegit.git_repo.index.write()

    def copy_synced_content_to_distgit_directory(self, synced_files: List[str]) -> None:
        """
        Copy files from source-git to destination directory.
        """
        for file in synced_files:
            file_in_working_dir = os.path.join(self.sourcegit.working_dir, file)
            logger.debug(f"Copying '{file_in_working_dir}' to distgit.")
            if os.path.isdir(file_in_working_dir):
                copy_tree(src=file_in_working_dir, dst=self.distgit.working_dir)
            elif os.path.isfile(file_in_working_dir):
                shutil.copy2(
                    file_in_working_dir, os.path.join(self.distgit.working_dir, file)
                )

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
        self.distgit.git_repo.git.add("-A")
        self.distgit.git_repo.index.write()
        # TODO: implement signing properly: we need to create a cert for the bot, distribute it to the container,
        #       prepare git config and then we can start signing
        # TODO: make -s configurable
        self.distgit.git_repo.git.commit("-s", "-m", main_msg, "-m", msg)

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
            logger.info(f"new comment added on PR {pr.id} ({pr.url})")
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
        if "origin-fork" not in [
            remote.name for remote in self.distgit.git_repo.remotes
        ]:
            self.distgit.git_repo.create_remote(
                name="origin-fork", url=project_fork.get_git_urls()["ssh"]
            )

        # I suggest to comment this one while testing when the push is not needed
        self.distgit.git_repo.remote("origin-fork").push(
            refspec=branch_name, force=branch_name in project_fork.get_branches()
        )

    def __enter__(self) -> Transformator:
        return self

    def __exit__(self, *args) -> None:
        self.clean()

    def get_latest_upstream_version(self):
        return versioneers_runner.run(
            versioneer=None, package_name=self.package_name, category=None
        )
