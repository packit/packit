import os
import shutil
import subprocess
import tempfile
# decorator for cached properties, in python >=3.8 use cached_property
from functools import lru_cache

import git


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

    def clean(self):
        print(f"Cleaning: {self.temp_dir}")
        shutil.rmtree(self.temp_dir)
        self._temp_dir = None

    def create_archive(self, path=None, name="{project}-{version}.tar.gz", prefix=None):
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
        redhat_dir = os.path.join(self.repo.working_tree_dir, "redhat")
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
    def get_commits_to_upstream(self, upstream):
        upstream_ref = f"origin/{upstream}"
        if upstream_ref not in self.repo.refs:
            raise Exception(f"Upstream {upstream_ref} not found.")

        commits = list(
            self.repo.iter_commits(rev=f"{upstream_ref}..{self.branch}",
                                   first_parent=True,
                                   reverse=True))
        commits.insert(0, self.repo.refs[f"{upstream_ref}"].commit)

        print(f"Delta ({upstream_ref}..{self.branch}): {len(commits)}")
        return commits

    def create_patches(self, upstream):
        commits = self.get_commits_to_upstream(upstream)
        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            git_diff_cmd = ["git", "diff", "--patch", parent.hexsha, commit.hexsha,
                            "--", ".", '":(exclude)redhat"']
            print(" ".join(git_diff_cmd))
            diff = subprocess.check_output(git_diff_cmd, cwd=self.repo.working_tree_dir).decode()

            patch_name = f"patch-{i+1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(self.dest_dir, patch_name)

            print(f"PATCH: {patch_path}")
            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)

    def clone_dist_git_repo(self, dist_git_url):
        return git.repo.Repo.clone_from(url=dist_git_url,
                                        to_path=self.dest_dir)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()
