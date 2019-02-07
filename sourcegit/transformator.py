from __future__ import annotations

import logging
import os
import shutil
import tempfile
# decorator for cached properties, in python >=3.8 use cached_property
from distutils.dir_util import copy_tree
from functools import lru_cache

import git

from sourcegit.utils import get_rev_list_kwargs, FedPKG, run_command

logger = logging.getLogger(__name__)


class Transformator:
    def __init__(self,
                 upstream_name,
                 package_name=None,
                 branch=None,
                 version=None,
                 dest_dir=None,
                 dist_git_url=None,
                 fas_username=None,
                 url=None,
                 repo=None,
                 rev_list_option=None):

        self._repo = repo
        if repo:
            self._branch = branch or repo.active_branch
            self.repo_url = url or list(repo.remote().urls)[0]
        else:
            self._branch = branch
            self.repo_url = url

        self._version = version
        self._temp_dir = None
        self.rev_list_option_args = get_rev_list_kwargs(rev_list_option or ["first_parent"])

        self.fas_username = fas_username

        self.upstream_name = upstream_name
        self.package_name = package_name or upstream_name
        self.dist_git_url = dist_git_url
        self.dest_dir = dest_dir or tempfile.mkdtemp()

    @property
    def branch(self):
        """
        Source branch in the source-git repo.
        """
        if not self._branch:
            self._branch = f"upstream-{self.version}"
        return self._branch

    @property
    def repo(self):
        """
        Repository used as a source.
        """
        if not self._repo:
            repo_path = os.path.join(self.temp_dir, self.upstream_name)
            logger.info(f"Cloning source-git repo: {self.repo_url} ({self.branch})-> {repo_path}")
            self._repo = git.repo.Repo.clone_from(url=self.repo_url,
                                                  to_path=repo_path,
                                                  branch=self.branch,
                                                  tags=True)
        return self._repo

    @property
    @lru_cache()
    def dist_git_repo(self):
        """
        Clone the dist_git repository to the destination dir and return git.Repo instance

        :return: git.Repo instance
        """
        return self.clone_dist_git_repo()

    @property
    def temp_dir(self):
        """
        Dir used for storing temp. content. e.g. source-git repo.
        """
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp()
            logger.debug(f"Creating temp dir: {self._temp_dir}")
        return self._temp_dir

    @property
    @lru_cache()
    def archive(self):
        """
        Path of the archive generated from the source-git.
        If not exists, the archive will be created in the destination directory.
        """
        archive = self.create_archive()
        return archive

    @property
    @lru_cache()
    def redhat_source_git_dir(self):
        """
        Git dir with the source-git repo content.
        """
        return os.path.join(self.repo.working_tree_dir, "redhat")

    @property
    @lru_cache()
    def version(self):
        return self._version or self.version_from_specfile

    @property
    @lru_cache()
    def version_from_specfile(self):
        """
        Version extracted from the specfile.
        """
        specfile_path = os.path.join(self.redhat_source_git_dir, f"{self.package_name}.spec")
        version_raw = run_command(cmd=["rpmspec", "-q", "--qf", "'%{version}\\n'", "--srpm",
                                       specfile_path],
                                  output=True,
                                  fail=True)
        version = version_raw.strip("'\\\n")
        return version

    @property
    @lru_cache()
    def fedpkg(self):
        """
        Instance of the FedPKG class (wrapper on top of the fedpkg command.)
        """
        return FedPKG(fas_username=self.fas_username,
                      repo_path=self.dist_git_url,
                      directory=self.dest_dir)

    def clean(self):
        """
        Clean te temporary dir.
        """
        logger.debug(f"Cleaning: {self.temp_dir}")
        shutil.rmtree(self.temp_dir)
        self._temp_dir = None

    def create_archive(self, path=None, name="{project}-{version}.tar.gz"):
        """
        Create archive from the provided git repo. The archive needs to be able to be used to build
        the project using rpmbuild command. The expectation is that the directory within the archive
        should be named {project}-{version}.

        :return: str, path to the archive
        """
        archive_name = name.format(project=self.upstream_name,
                                   version=self.version)
        archive_path = path or os.path.join(self.dest_dir, archive_name)

        self.add_exclude_redhat_to_gitattributes()

        with open(archive_path, 'wb') as fp:
            self.repo.archive(fp, prefix=f"./{self.upstream_name}/", worktree_attributes=True)

        logger.info(f"Archive created: {archive_path}")
        return archive_path

    def add_exclude_redhat_to_gitattributes(self):
        """
        Add a line to .gitattributes to export-ignore redhat dir.
        """
        logger.debug("Adding 'redhat/ export-ignore' to .gitattributes")
        gitattributes_path = os.path.join(self.repo.working_tree_dir, '.gitattributes')
        with open(gitattributes_path, 'a') as gitattributes_file:
            gitattributes_file.writelines(["redhat/ export-ignore\n"])

    @lru_cache()
    def create_srpm(self):
        logger.debug("Start creating og the SRPM.")
        archive = self.create_archive()
        logger.debug(f"Using archive: {archive}")

        redhat_dir = self.redhat_source_git_dir
        spec = os.path.join(redhat_dir, f"{self.package_name}.spec")
        run_command(cmd=["rpmbuild", "-bs", f"{spec}",
                         "--define", f"_sourcedir {redhat_dir}",
                         "--define", f"_specdir {redhat_dir}",
                         "--define", f"_buildir {redhat_dir}",
                         "--define", f"_srcrpmdir {self.dest_dir}",
                         "--define", f"_rpmdir {redhat_dir}",
                         ],
                    fail=True)

    @lru_cache()
    def get_commits_to_upstream(self, upstream, add_usptream_head_commit=False):
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
                raise Exception(f"Upstream {upstream_ref} branch nor {upstream} tag not found.")

        commits = list(
            self.repo.iter_commits(rev=f"{upstream_ref}..{self.branch}",
                                   reverse=True,
                                   **self.rev_list_option_args))
        if add_usptream_head_commit:
            commits.insert(0, self.repo.refs[f"{upstream_ref}"].commit)

        logger.debug(f"Delta ({upstream_ref}..{self.branch}): {len(commits)}")
        return commits

    @lru_cache()
    def clone_dist_git_repo(self):
        """
        Clone the dist_git repository to the destination dir and return git.Repo instance

        :return: git.Repo instance
        """
        # TODO: optimize cloning: single branch and last 3 commits?
        if os.path.isdir(os.path.join(self.dest_dir, ".git")):
            logger.info(f"Dist-git already present: {self.dest_dir}")
            return git.repo.Repo(self.dest_dir)

        logger.info(f"Cloning dist-git repo: {self.dist_git_url} -> {self.dest_dir}")
        return git.repo.Repo.clone_from(url=self.dist_git_url,
                                        to_path=self.dest_dir,
                                        tags=True)

    def create_patches(self, upstream=None, rev_list_option=None):
        """
        Create patches from downstream commits.

        :param upstream: str -- git branch or tag
        :param rev_list_option: [str] -- list of options forwarded to `git rev-list`
                                in form `key` or `key=val`.
        :return: [(patch_name, msg)] list of created patches (tuple of the file name and commit msg)
        """

        upstream = upstream or self.version_from_specfile
        commits = self.get_commits_to_upstream(upstream, add_usptream_head_commit=True)
        patch_list = []
        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            patch_name = f"{i+1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(self.dest_dir, patch_name)
            patch_msg = f"{commit.summary}\nAuthor: {commit.author.name} <{commit.author.email}>"

            logger.debug(f"PATCH: {patch_name}\n{patch_msg}")
            diff = run_command(cmd=["git", "diff", "--patch", parent.hexsha, commit.hexsha,
                                    "--", ".", '":(exclude)redhat"'],
                               cwd=self.repo.working_tree_dir,
                               output=True)

            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)
            patch_list.append((patch_name, patch_msg))

        return patch_list

    def add_patches_to_specfile(self, patch_list):
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [(patch_name, msg)]
        """
        specfile_path = os.path.join(self.dest_dir, f"{self.package_name}.spec")

        with open(file=specfile_path, mode="r+") as spec_file:
            last_source_position = None
            line = spec_file.readline()
            while line:
                if line.startswith("Source"):
                    last_source_position = spec_file.tell()

                line = spec_file.readline()

            spec_file.seek(last_source_position)
            rest_of_the_file = spec_file.read()
            spec_file.seek(last_source_position)

            spec_file.write("\n\n# PATCHES FROM SOURCE GIT:\n")
            for i, (patch, msg) in enumerate(patch_list):
                commented_msg = "\n# " + '\n# '.join(msg.split('\n')) + "\n"
                spec_file.write(commented_msg)
                spec_file.write(f"Patch{i+1:04d}: {patch}\n")

            spec_file.write(rest_of_the_file)

        logger.info(f"Patches ({len(patch_list)}) added to the specfile ({specfile_path})")

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

    def upload_archive_to_lookaside_cache(self, keytab):
        """
        Upload the archive to the lookaside cache using fedpkg.
        (If not exists, the archive will be created.)
        """
        logger.info("Uploading the archive to lookaside cache.")
        self.fedpkg.init_ticket(keytab)
        self.fedpkg.new_sources(sources=self.archive,
                                fail=False)

    def commit_distgit(self, title, msg):
        main_msg = f"[source-git] {title}"
        self.dist_git_repo.git.add("-A")
        self.dist_git_repo.index.write()
        # TODO: implement signing properly: we need to create a cert for the bot, distribute it to the container,
        #       prepare git config and then we can start signing
        # TODO: make -s configurable
        self.dist_git_repo.git.commit("-s", "-m", main_msg, "-m", msg)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()
