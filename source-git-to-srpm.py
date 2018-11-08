"""
This script is meant to accept source git repo with a branch as an input and build it in Fedora

It is expected to do this:

1. clone the repo
2. create archive out of the sources
3. create SRPM
4. submit the SRPM to koji
5. wait for the build to finish
6. update github status to reflect the result of the build
"""
import os
import shutil
import subprocess
import sys
import tempfile

import git


class Transformator:
    def __init__(self, url,
                 upstream_name,
                 package_name,
                 version):

        self.repo_url = url

        self.upstream_name = upstream_name
        self.package_name = package_name

        self.branch = f"upstream-{version}"
        self.version = version

        self._repo = None
        self._temp_dir = None
        self._archive = None

    @property
    def repo(self):
        if not self._repo:
            repo_path = os.path.join(self.temp_dir, self.upstream_name)
            self._repo = git.repo.Repo.clone_from(url=self.repo_url,
                                                  to_path=repo_path,
                                                  branch=self.branch,
                                                  depth=1)

            self._repo = git.Repo(repo_path)

        return self._repo

    @property
    def temp_dir(self):
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp()
            print(f"Creating: {self.temp_dir}")
        return self._temp_dir

    @property
    def archive(self):
        if not self._archive:
            self.create_archive()

        return self.archive

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
        archive_path = path or os.path.join(self.repo.working_tree_dir, "redhat", archive_name)

        with open(archive_path, 'wb') as fp:
            self.repo.archive(fp, prefix=f"./{self.upstream_name}/")

        self._archive = archive_path
        print(f"Archive: {archive_path}")
        return archive_path

    def create_srpm(self):
        self.create_archive()
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


def usage():
    print(f"Usage: {sys.argv[0]} GIT_REPO UPSTREAM_NAME PACKAGE_NAME VERSION")
    return -1


def main():
    try:
        repo_url = sys.argv[1]
        upstream_name = sys.argv[2]
        package_name = sys.argv[3]
        version = sys.argv[4]
    except IndexError:
        return usage()

    t = Transformator(url=repo_url,
                      upstream_name=upstream_name,
                      package_name=package_name,
                      version=version)

    try:
        t.create_srpm()
    finally:
        t.clean()

    return 0


if __name__ == '__main__':
    sys.exit(main())
