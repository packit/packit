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
import shutil
import sys
import subprocess
import tempfile


class Transformator:
    def __init__(self, repo_name, branch):
        self.t = tempfile.mkdtemp()
        self.repo_name = repo_name
        self.branch = branch

    def clean(self):
        shutil.rmtree(self.t)

    def create_srpm(self):
        srpm = create_srpm()
        return srpm


def check_out_repo(repo_name, branch, target_dir):
    url = f"https://github.com/{repo_name}.git"
    cmd = [
        "git",
        "clone",
        "-b", branch,
        "--depth", "1",
        url,
        target_dir

    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_archive(path):
    """
    Create archive from the provided git repo. The archive needs to be able to be used to build
    the project using rpmbuild command. The expectation is that the directory within the archive
    should be named {project}-{branch}.

    :return: str, path to the archive
    """


def create_srpm():
    """
    Create SRPM using provided spec file and archive.

    :return: path to srpm
    """


def usage():
    print(f"Usage: {sys.argv[0]} GITHUB_REPO/NAME BRANCH")
    return -1


def main():
    try:
        repo_name = sys.argv[1]
        branch = sys.argv[2]
    except IndexError:
        return usage()

    t = Transformator(repo_name, branch)
    try:
        srpm_path = t.create_srpm()
        # TODO: submit the srpm as a build to koji and wait for it to complete
        # TODO: update status on github to reflect whether the build was successful or not
    finally:
        t.clean()

    check_out_repo(repo_name, branch)

    return 0


if __name__ == '__main__':
    sys.exit(main())
