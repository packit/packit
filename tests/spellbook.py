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

import shutil
import git
from pathlib import Path

from click.testing import CliRunner

from packit.cli.packit_base import packit_base
from packit.config import Config
from packit.utils import cwd, run_command

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
EMPTY_CHANGELOG = DATA_DIR / "empty_changelog"
DISTGIT = DATA_DIR / "dist_git"
UP_COCKPIT_OSTREE = DATA_DIR / "cockpit-ostree"
UP_OSBUILD = DATA_DIR / "osbuild"
UP_SNAPD = DATA_DIR / "snapd"
TARBALL_NAME = "beerware-0.1.0.tar.gz"
SOURCEGIT_UPSTREAM = DATA_DIR / "sourcegit" / "upstream"
SOURCEGIT_SOURCEGIT = DATA_DIR / "sourcegit" / "source_git"
DG_OGR = DATA_DIR / "dg-ogr"
SPECFILE = DATA_DIR / "upstream_git/beer.spec"
UPSTREAM_SPEC_NOT_IN_ROOT = DATA_DIR / "spec_not_in_root/upstream"


def git_set_user_email(directory):
    repo = git.Repo(directory)
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    repo.config_writer().set_value("user", "name", "Packit Test Suite").release()


def get_test_config():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._github_token = "test"
    return conf


def git_add_and_commit(directory, message):
    repo = git.Repo(directory)
    repo.git.add(".")
    try:
        repo.git.commit("-m", message)
    except git.exc.GitCommandError:
        pass
        # nothing to commit


def initiate_git_repo(
    directory,
    tag=None,
    upstream_remote="https://lol.wat",
    push=False,
    copy_from: str = None,
    remotes=None,
):
    """
    Initiate a git repo for testing.

    :param directory: path to the git repo
    :param tag: if set, tag the latest commit with this tag
    :param upstream_remote: name of the origin - upstream remote (not used when remotes are set)
    :param remotes: provide list of tuples (name, remote_url)
    :param push: push to the remote?
    :param copy_from: source tree to copy to the newly created git repo
    """

    if remotes is None:
        remotes = [("origin", upstream_remote)]

    if copy_from:
        shutil.copytree(copy_from, directory)

    repo = git.Repo.init(directory)

    Path(directory).joinpath("README").write_text("Best upstream project ever!")
    git_set_user_email(directory)
    repo.git.add(".")
    repo.git.commit("-m", "initial commit")
    if tag:
        repo.create_tag(tag)

    for name, url in remotes:
        try:
            repo.create_remote(name, url=url)
        except git.exc.GitCommandError:
            pass
            # remote already added

    if push and tag:
        remotes = repo.remotes
        for remote in remotes:
            try:
                remote.fetch()
            except git.exc.GitCommandError:
                pass
                # can't resoleve remote url
        # tox strips some env vars so your user gitconfig is not picked up
        # hence we need to be very explicit with git commands here
        for remote in remotes:
            if remote.name == "origin":
                try:
                    remote.push(repo.tags)
                except git.exc.GitCommandError:
                    pass
                    # con't resolve url
                    # or tag
                break


def prepare_dist_git_repo(directory, push=True):
    repo = git.Repo(directory)
    branch = repo.create_head("f30")
    branch.checkout()
    if push:
        for remote in repo.remotes:
            if remote.name == "origin":
                remote.push("f30:f30")
                break


def call_packit(fnc=None, parameters=None, envs=None, working_dir=None):
    working_dir = working_dir or "."
    fnc = fnc or packit_base
    runner = CliRunner()
    envs = envs or {}
    parameters = parameters or []
    # catch exceptions enables debugger
    with cwd(working_dir):
        return runner.invoke(fnc, args=parameters, env=envs, catch_exceptions=False)


def build_srpm(path: Path):
    run_command(["rpmbuild", "--rebuild", str(path)])


def can_a_module_be_imported(module_name):
    """ can a module be imported? """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False
