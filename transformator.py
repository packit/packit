import os
import shutil
import subprocess
import tempfile
# decorator for cached properties, in python >=3.8 use cached_property
from distutils.dir_util import copy_tree
from functools import lru_cache

import git

from utils import get_rev_list_kwargs


class Transformator:
    def __init__(self, url,
                 upstream_name,
                 package_name,
                 version,
                 dest_dir=None):

        self.repo_url = url

        self.upstream_name = upstream_name
        self.package_name = package_name
        self.dest_dir = dest_dir or tempfile.mkdtemp()

        self.branch = f"upstream-{version}"
        self.version = version

        self._temp_dir = None

    @property
    @lru_cache()
    def repo(self):
        repo_path = os.path.join(self.temp_dir, self.upstream_name)
        return git.repo.Repo.clone_from(url=self.repo_url,
                                        to_path=repo_path,
                                        branch=self.branch)

    @property
    def temp_dir(self):
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp()
            print(f"Creating: {self._temp_dir}")
        return self._temp_dir

    @property
    @lru_cache()
    def archive(self):
        archive = self.create_archive()
        print(f"Creating archive: {archive}")
        return archive

    @property
    @lru_cache()
    def redhat_source_git_dir(self):
        return os.path.join(self.repo.working_tree_dir, "redhat")

    @property
    @lru_cache()
    def version_from_specfile(self):
        specfile_path = os.path.join(self.redhat_source_git_dir, f"{self.package_name}.spec")
        get_version_from_spec_cmd = ["rpmspec", "-q", "--qf", "'%{version}\\n'", "--srpm",
                                     specfile_path]
        print(f"CMD: {' '.join(get_version_from_spec_cmd)}")
        version_raw = subprocess.check_output(get_version_from_spec_cmd).decode()
        version = version_raw.strip("'\\\n")
        return version

    def clean(self):
        print(f"Cleaning: {self.temp_dir}")
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

        print(f"Archive: {archive_path}")
        return archive_path

    def add_exclude_redhat_to_gitattributes(self):
        gitattributes_path = os.path.join(self.repo.working_tree_dir, '.gitattributes')
        with open(gitattributes_path, 'a') as gitattributes_file:
            gitattributes_file.writelines(["redhat/ export-ignore\n"])

    @lru_cache()
    def create_srpm(self):
        # force the archive creation
        archive = self.archive
        print(f"Used archive: {archive}")

        pwd = os.path.abspath(os.path.curdir)
        print(f"PWD: {pwd}")
        redhat_dir = self.redhat_source_git_dir
        spec = os.path.join(redhat_dir, f"{self.package_name}.spec")
        rpmbuild_cmd = ["rpmbuild", "-bs", f"{spec}",
                        "--define", f"_sourcedir {redhat_dir}",
                        "--define", f"_specdir {redhat_dir}",
                        "--define", f"_buildir {redhat_dir}",
                        "--define", f"_srcrpmdir {pwd}",
                        "--define", f"_rpmdir {redhat_dir}",
                        ]
        print(f"CMD: {' '.join(rpmbuild_cmd)}")
        try:
            subprocess.call(rpmbuild_cmd)
        except:
            raise

    @lru_cache()
    def get_commits_to_upstream(self, upstream, rev_list_option=None):
        """
        Return the list of commits from current branch to upstream rev/tag.

        :param upstream: str -- git branch or tag
        :param rev_list_option: [str] -- list of options forwarded to `git rev-list`
                                in form `key` or `key=val`.
        :return: list of commits (last commit on the current branch.).
        """

        rev_list_option = rev_list_option or ["first_parent"]
        rev_list_option_args = get_rev_list_kwargs(rev_list_option)

        if upstream in self.repo.tags:
            upstream_ref = upstream
        else:
            upstream_ref = f"origin/{upstream}"
            if upstream_ref not in self.repo.refs:
                raise Exception(f"Upstream {upstream_ref} branch nor {upstream} tag not found.")

        commits = list(
            self.repo.iter_commits(rev=f"{upstream_ref}..{self.branch}",
                                   first_parent=True,
                                   reverse=True))
        commits.insert(0, self.repo.refs[f"{upstream_ref}"].commit)

        print(f"Delta ({upstream_ref}..{self.branch}): {len(commits)}")
        return commits

    def create_patches(self, upstream=None):

        upstream = upstream or self.version_from_specfile

        commits = self.get_commits_to_upstream(upstream)
        patch_list = []
        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            git_diff_cmd = ["git", "diff", "--patch", parent.hexsha, commit.hexsha,
                            "--", ".", '":(exclude)redhat"']
            print(" ".join(git_diff_cmd))
            diff = subprocess.check_output(git_diff_cmd, cwd=self.repo.working_tree_dir).decode()

            patch_name = f"{i+1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(self.dest_dir, patch_name)
            patch_list.append(
                (patch_name,
                 f"{commit.summary}\nAuthor: {commit.author.name} <{commit.author.email}>")
            )

            print(f"PATCH: {patch_path}")
            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)

        return patch_list

    def clone_dist_git_repo(self, dist_git_url):
        return git.repo.Repo.clone_from(url=dist_git_url,
                                        to_path=self.dest_dir)

    def add_patches_to_specfile(self, patch_list):
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

        print(f"SPECFILE UPDATED: {specfile_path}")

    def copy_redhat_content_to_dest_dir(self):
        copy_tree(src=self.redhat_source_git_dir,
                  dst=self.dest_dir)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()
