# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
A book with our finest spells
"""
import subprocess
from pathlib import Path

from click.testing import CliRunner

from packit.cli.packit_base import packit_base
from packit.config import Config

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
DISTGIT = DATA_DIR / "dist_git"
TARBALL_NAME = "beerware-0.1.0.tar.gz"
SOURCEGIT_UPSTREAM = DATA_DIR / "sourcegit" / "upstream"
SOURCEGIT_SOURCEGIT = DATA_DIR / "sourcegit" / "source_git"


def git_set_user_email(directory):
    subprocess.check_call(
        ["git", "config", "user.email", "test@example.com"], cwd=directory
    )
    subprocess.check_call(
        ["git", "config", "user.name", "Packit Test Suite"], cwd=directory
    )


def get_test_config():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._pagure_fork_token = "test"
    conf._github_token = "test"
    return conf


def git_add_and_commit(directory, message):
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", message], cwd=directory)


def initiate_git_repo(
    directory, tag=None, upstream_remote="https://lol.wat", push=False
):
    """
    Initiate a git repo for testing.

    :param directory: path to the git repo
    :param tag: if set, tag the latest commit with this tag
    :param upstream_remote: name of the origin - upstream remote
    :param push: push to the remote?
    """
    subprocess.check_call(["git", "init", "."], cwd=directory)
    Path(directory).joinpath("README").write_text("Best upstream project ever!")
    git_set_user_email(directory)
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=directory)
    if tag:
        subprocess.check_call(["git", "tag", tag], cwd=directory)
    subprocess.check_call(
        ["git", "remote", "add", "origin", upstream_remote], cwd=directory
    )
    if push:
        subprocess.check_call(["git", "fetch", "origin"], cwd=directory)
        # tox strips some env vars so your user gitconfig is not picked up
        # hence we need to be very explicit with git commands here
        subprocess.check_call(
            ["git", "push", "-u", "origin", "master:master"], cwd=directory
        )


def prepare_dist_git_repo(directory):
    subprocess.check_call(["git", "branch", "f30"], cwd=directory)
    subprocess.check_call(["git", "push", "-u", "origin", "f30:f30"], cwd=directory)


def can_a_module_be_imported(module_name):
    """ can a module be imported? """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def call_packit(fnc=None, parameters=None, envs=None):
    fnc = fnc or packit_base
    runner = CliRunner()
    envs = envs or {}
    parameters = parameters or []
    # catch exceptions enables debugger
    return runner.invoke(fnc, args=parameters, env=envs, catch_exceptions=False)


def call_real_packit(parameters=None, envs=None, cwd=None):
    """ invoke packit in a subprocess """
    cmd = ["python3", "-m", "packit.cli.packit_base"] + parameters
    return subprocess.check_call(cmd, env=envs, cwd=cwd)


def does_bumpspec_know_new():
    """ does rpmdev-bumpspec know --new? """
    h = subprocess.check_output(["rpmdev-bumpspec", "--help"])
    return b"--new" in h
