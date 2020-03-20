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
import subprocess
from pathlib import Path

from click.testing import CliRunner

from packit.cli.packit_base import packit_base
from packit.config import Config
from packit.utils import cwd, run_command

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
UPSTREAM_WITH_MUTLIPLE_SOURCES = DATA_DIR / "upstream_git_with_multiple_sources"
UPSTREAM_WEIRD_SOURCES = DATA_DIR / "upstream_git_weird_sources"
EMPTY_CHANGELOG = DATA_DIR / "empty_changelog"
DISTGIT = DATA_DIR / "dist_git"
UP_COCKPIT_OSTREE = DATA_DIR / "cockpit-ostree"
UP_OSBUILD = DATA_DIR / "osbuild"
UP_SNAPD = DATA_DIR / "snapd"
UP_EDD = DATA_DIR / "edd"
UP_VSFTPD = DATA_DIR / "vsftpd"
NAME_VERSION = "beerware-0.1.0"
TARBALL_NAME = f"{NAME_VERSION}.tar.gz"
SOURCEGIT_UPSTREAM = DATA_DIR / "sourcegit" / "upstream"
SOURCEGIT_SOURCEGIT = DATA_DIR / "sourcegit" / "source_git"
DG_OGR = DATA_DIR / "dg-ogr"
SPECFILE = DATA_DIR / "upstream_git/beer.spec"
UPSTREAM_SPEC_NOT_IN_ROOT = DATA_DIR / "spec_not_in_root/upstream"
SYNC_FILES = DATA_DIR / "sync_files"


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
    conf._github_token = "test"
    return conf


def git_add_and_commit(directory, message):
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", message], cwd=directory)


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
    subprocess.check_call(["git", "init", "."], cwd=directory)
    for i in range(3):
        subprocess.check_call(
            ["git", "commit", "--allow-empty", "-m", f"empty commit #{i}"],
            cwd=directory,
        )
    directory_path = Path(directory)
    directory_path.joinpath("README").write_text("Best upstream project ever!")
    # this file is in the tarball
    directory_path.joinpath("hops").write_text("Cascade\n")
    git_set_user_email(directory)
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", "commit with data"], cwd=directory)
    if tag:
        subprocess.check_call(
            ["git", "tag", "-a", "-m", f"tag {tag}, tests", tag], cwd=directory
        )

    for name, url in remotes:
        subprocess.check_call(["git", "remote", "add", name, url], cwd=directory)

    if push:
        subprocess.check_call(["git", "fetch", "origin"], cwd=directory)
        # tox strips some env vars so your user gitconfig is not picked up
        # hence we need to be very explicit with git commands here
        subprocess.check_call(
            ["git", "push", "--tags", "-u", "origin", "master:master"], cwd=directory
        )


def create_merge_commit_in_source_git(sg: Path, go_nuts=False):
    """
    create merge commit in the provided source-git repo

    :param sg: the repo
    :param go_nuts: if True, create such merge that Franta won't be able to sleep
    """
    hops = sg.joinpath("hops")
    subprocess.check_call(["git", "checkout", "-B", "new-changes"], cwd=sg)
    hops.write_text("Amarillo\n")
    git_add_and_commit(directory=sg, message="switching to amarillo hops")
    hops.write_text("Citra\n")
    git_add_and_commit(directory=sg, message="actually, let's do citra")
    subprocess.check_call(["git", "checkout", "master"], cwd=sg)
    subprocess.check_call(
        ["git", "merge", "--no-ff", "-m", "MERGE COMMIT!", "new-changes"], cwd=sg,
    )
    if go_nuts:
        malt = sg.joinpath("malt")
        subprocess.check_call(["git", "checkout", "-B", "ugly-merge", "0.1.0^"], cwd=sg)
        malt.write_text("Munich\n")
        git_add_and_commit(directory=sg, message="let's start with the Munich malt")
        subprocess.check_call(["git", "checkout", "master"], cwd=sg)
        subprocess.check_call(
            ["git", "merge", "--no-ff", "-m", "ugly merge commit", "ugly-merge"],
            cwd=sg,
        )
        subprocess.check_call(
            ["git", "checkout", "-B", "ugly-merge2", "HEAD~2"], cwd=sg
        )
        malt.write_text("Pilsen\n")
        git_add_and_commit(directory=sg, message="let's try Pilsen instead")
        subprocess.check_call(["git", "checkout", "master"], cwd=sg)
        subprocess.check_call(
            [
                "git",
                "merge",
                "-Xours",
                "--no-ff",
                "-m",
                "ugly merge commit #2",
                "ugly-merge2",
            ],
            cwd=sg,
        )
        # M─┐ [master] ugly merge commit #2
        # │ o [ugly-merge2] let's try Pilsen instead
        # M─│─┐ ugly merge commit
        # │ │ o [ugly-merge] let's start with the Munich malt
        # M─│─│─┐ MERGE COMMIT!
        # │ │ │ o [new-changes] actually, let's do citra
        # │ │ │ o switching to amarillo hops
        # o─┴─│─┘ sourcegit content
        # o ┌─┘ <0.1.0> commit with data
        # o─┘ empty commit #2


def prepare_dist_git_repo(directory, push=True):
    subprocess.check_call(["git", "branch", "f30"], cwd=directory)
    if push:
        subprocess.check_call(["git", "push", "-u", "origin", "f30:f30"], cwd=directory)


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
    run_command(["rpmbuild", "--rebuild", str(path)], output=True)


def can_a_module_be_imported(module_name):
    """ can a module be imported? """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False
