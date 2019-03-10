"""
A book with our finest spells
"""
import subprocess
from pathlib import Path

from packit.config import Config


TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
DISTGIT = DATA_DIR / "dist_git"
TARBALL_NAME = "beerware-0.1.0.tar.gz"


def git_set_user_email(directory):
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=directory)
    subprocess.check_call(["git", "config", "user.name", "Packit Test Suite"], cwd=directory)


def get_test_config():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._pagure_fork_token = "test"
    conf._github_token = "test"
    return conf


def git_add_n_commit(directory, tag=None, upstream_remote="https://lol.wat", push=False):
    """
    Initiate a git repo for testing.

    :param directory: path to the git repo
    :param tag: if set, tag the latest commit with this tag
    :param upstream_remote: name of the origin - upstream remote
    :param push: push to the remote?
    """
    subprocess.check_call(["git", "init", "."], cwd=directory)
    git_set_user_email(directory)
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=directory)
    if tag:
        subprocess.check_call(["git", "tag", tag], cwd=directory)
    subprocess.check_call(["git", "remote", "add", "origin", upstream_remote], cwd=directory)
    if push:
        subprocess.check_call(["git", "fetch", "origin"], cwd=directory)
        # tox strips some env vars so your user gitconfig is not picked up
        # hence we need to be very explicit with git commands here
        subprocess.check_call(["git", "push", "-u", "origin", "master:master"], cwd=directory)


def prepare_dist_git_repo(directory):
    subprocess.check_call(["git", "branch", "f30"], cwd=directory)
    subprocess.check_call(["git", "push", "-u", "origin", "f30:f30"], cwd=directory)
