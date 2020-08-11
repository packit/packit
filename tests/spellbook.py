# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
from packit.patches import PatchMetadata

from packit.cli.packit_base import packit_base
from packit.config import Config
from packit.utils.commands import cwd, run_command

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


def create_git_am_style_history(sg: Path):
    """
    create merge commit in the provided source-git repo

    :param sg: the repo
    """
    hops = sg.joinpath("hops")
    hops.write_text("Amarillo\n")
    git_add_and_commit(directory=sg, message="switching to amarillo hops")

    hops.write_text("Citra\n")
    meta = PatchMetadata(
        name="citra.patch", squash_commits=True, present_in_specfile=True
    )
    git_add_and_commit(directory=sg, message=meta.commit_message)

    malt = sg.joinpath("malt")
    malt.write_text("Munich\n")
    meta = PatchMetadata(
        name="malt.patch", squash_commits=True, present_in_specfile=True
    )
    git_add_and_commit(directory=sg, message=meta.commit_message)

    malt.write_text("Pilsen\n")
    git_add_and_commit(directory=sg, message="using Pilsen malt")

    malt.write_text("Vienna\n")
    git_add_and_commit(directory=sg, message="actually Vienna malt could be good")

    malt.write_text("Weyermann\n")
    meta = PatchMetadata(
        name="0001-m04r-malt.patch", squash_commits=True, present_in_specfile=True
    )
    git_add_and_commit(directory=sg, message=meta.commit_message)


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


ALL_KOJI_TARGETS_SNAPSHOT = [
    "dist-6E-epel",
    "dist-6E-epel-build",
    "dist-6E-epel-testing-candidate",
    "dist-6E-epel-testing-candidate",
    "dist-6E-epel-build",
    "dist-6E-epel-testing-candidate",
    "el6-candidate",
    "dist-6E-epel-build",
    "dist-6E-epel-testing-candidate",
    "eln",
    "eln-build",
    "eln-updates-candidate",
    "eln-candidate",
    "eln-build",
    "eln-updates-candidate",
    "eln-rebuild",
    "eln-build",
    "eln-rebuild",
    "epel6-infra",
    "epel6-infra",
    "epel6-infra-candidate",
    "epel7",
    "epel7-build",
    "epel7-testing-candidate",
    "epel7-candidate",
    "epel7-build",
    "epel7-testing-candidate",
    "epel7-infra",
    "epel7-infra-build",
    "epel7-infra-candidate",
    "epel7-infra-mailman",
    "epel7-infra-mailman",
    "epel7-infra-mailman-candidate",
    "epel8",
    "epel8-build",
    "epel8-testing-candidate",
    "epel8-candidate",
    "epel8-build",
    "epel8-testing-candidate",
    "epel8-infra",
    "epel8-infra-build",
    "epel8-infra-candidate",
    "epel8-playground",
    "epel8-playground-build",
    "epel8-playground-pending",
    "epel8-playground-candidate",
    "epel8-playground-build",
    "epel8-playground-pending",
    "f30",
    "f30-build",
    "f30-updates-candidate",
    "f30-candidate",
    "f30-build",
    "f30-updates-candidate",
    "f30-container-candidate",
    "f30-container-build",
    "f30-container-updates-candidate",
    "f30-coreos-continuous",
    "f30-build",
    "f30-coreos-continuous",
    "f30-flatpak-candidate",
    "f30-build",
    "f30-flatpak-updates-candidate",
    "f30-infra",
    "f30-infra-build",
    "f30-infra-candidate",
    "f30-kde",
    "f30-kde",
    "f30-kde",
    "f30-rebuild",
    "f30-build",
    "f30-rebuild",
    "f31",
    "f31-build",
    "f31-updates-candidate",
    "f31-build-side-18630",
    "f31-build-side-18630",
    "f31-build-side-18630",
    "f31-build-side-23208",
    "f31-build-side-23208",
    "f31-build-side-23208",
    "f31-build-side-23528",
    "f31-build-side-23528",
    "f31-build-side-23528",
    "f31-build-side-23731",
    "f31-build-side-23731",
    "f31-build-side-23731",
    "f31-build-side-23745",
    "f31-build-side-23745",
    "f31-build-side-23745",
    "f31-candidate",
    "f31-build",
    "f31-updates-candidate",
    "f31-container-candidate",
    "f31-container-build",
    "f31-container-updates-candidate",
    "f31-coreos-continuous",
    "f31-build",
    "f31-coreos-continuous",
    "f31-flatpak-candidate",
    "f31-build",
    "f31-flatpak-updates-candidate",
    "f31-infra",
    "f31-infra-build",
    "f31-infra-candidate",
    "f31-kde",
    "f31-kde",
    "f31-kde",
    "f31-rebuild",
    "f31-build",
    "f31-rebuild",
    "f32",
    "f32-build",
    "f32-updates-candidate",
    "f32-build-side-14233",
    "f32-build-side-14233",
    "f32-build-side-14233",
    "f32-build-side-18049",
    "f32-build-side-18049",
    "f32-build-side-18049",
    "f32-build-side-18314",
    "f32-build-side-18314",
    "f32-build-side-18314",
    "f32-build-side-19863",
    "f32-build-side-19863",
    "f32-build-side-19863",
    "f32-build-side-19894",
    "f32-build-side-19894",
    "f32-build-side-19894",
    "f32-build-side-20363",
    "f32-build-side-20363",
    "f32-build-side-20363",
    "f32-build-side-23072",
    "f32-build-side-23072",
    "f32-build-side-23072",
    "f32-build-side-23076",
    "f32-build-side-23076",
    "f32-build-side-23076",
    "f32-build-side-23196",
    "f32-build-side-23196",
    "f32-build-side-23196",
    "f32-build-side-23526",
    "f32-build-side-23526",
    "f32-build-side-23526",
    "f32-build-side-23640",
    "f32-build-side-23640",
    "f32-build-side-23640",
    "f32-build-side-23729",
    "f32-build-side-23729",
    "f32-build-side-23729",
    "f32-build-side-23739",
    "f32-build-side-23739",
    "f32-build-side-23739",
    "f32-build-side-23743",
    "f32-build-side-23743",
    "f32-build-side-23743",
    "f32-build-side-23781",
    "f32-build-side-23781",
    "f32-build-side-23781",
    "f32-build-side-23801",
    "f32-build-side-23801",
    "f32-build-side-23801",
    "f32-build-side-23867",
    "f32-build-side-23867",
    "f32-build-side-23867",
    "f32-candidate",
    "f32-build",
    "f32-updates-candidate",
    "f32-container-candidate",
    "f32-container-build",
    "f32-container-updates-candidate",
    "f32-coreos-continuous",
    "f32-build",
    "f32-coreos-continuous",
    "f32-flatpak-candidate",
    "f32-build",
    "f32-flatpak-updates-candidate",
    "f32-gnome",
    "f32-gnome",
    "f32-gnome",
    "f32-infra",
    "f32-infra-build",
    "f32-infra-candidate",
    "f32-kde",
    "f32-kde",
    "f32-kde",
    "f32-rebuild",
    "f32-build",
    "f32-rebuild",
    "f33",
    "f33-build",
    "f33-updates-candidate",
    "f33-build-side-21982",
    "f33-build-side-21982",
    "f33-build-side-21982",
    "f33-build-side-22329",
    "f33-build-side-22329",
    "f33-build-side-22329",
    "f33-build-side-22337",
    "f33-build-side-22337",
    "f33-build-side-22337",
    "f33-build-side-23466",
    "f33-build-side-23466",
    "f33-build-side-23466",
    "f33-build-side-23544",
    "f33-build-side-23544",
    "f33-build-side-23544",
    "f33-build-side-23564",
    "f33-build-side-23564",
    "f33-build-side-23564",
    "f33-build-side-23572",
    "f33-build-side-23572",
    "f33-build-side-23572",
    "f33-build-side-23578",
    "f33-build-side-23578",
    "f33-build-side-23578",
    "f33-build-side-23580",
    "f33-build-side-23580",
    "f33-build-side-23580",
    "f33-build-side-23622",
    "f33-build-side-23622",
    "f33-build-side-23622",
    "f33-build-side-23628",
    "f33-build-side-23628",
    "f33-build-side-23628",
    "f33-build-side-23632",
    "f33-build-side-23632",
    "f33-build-side-23632",
    "f33-build-side-23634",
    "f33-build-side-23634",
    "f33-build-side-23634",
    "f33-build-side-23636",
    "f33-build-side-23636",
    "f33-build-side-23636",
    "f33-build-side-23677",
    "f33-build-side-23677",
    "f33-build-side-23677",
    "f33-build-side-23695",
    "f33-build-side-23695",
    "f33-build-side-23695",
    "f33-build-side-23715",
    "f33-build-side-23715",
    "f33-build-side-23715",
    "f33-build-side-23723",
    "f33-build-side-23723",
    "f33-build-side-23723",
    "f33-build-side-23737",
    "f33-build-side-23737",
    "f33-build-side-23737",
    "f33-build-side-23741",
    "f33-build-side-23741",
    "f33-build-side-23741",
    "f33-build-side-23785",
    "f33-build-side-23785",
    "f33-build-side-23785",
    "f33-build-side-23789",
    "f33-build-side-23789",
    "f33-build-side-23789",
    "f33-build-side-23793",
    "f33-build-side-23793",
    "f33-build-side-23793",
    "f33-build-side-23807",
    "f33-build-side-23807",
    "f33-build-side-23807",
    "f33-build-side-23821",
    "f33-build-side-23821",
    "f33-build-side-23821",
    "f33-build-side-23827",
    "f33-build-side-23827",
    "f33-build-side-23827",
    "f33-build-side-23829",
    "f33-build-side-23829",
    "f33-build-side-23829",
    "f33-build-side-23839",
    "f33-build-side-23839",
    "f33-build-side-23839",
    "f33-build-side-23847",
    "f33-build-side-23847",
    "f33-build-side-23847",
    "f33-build-side-23853",
    "f33-build-side-23853",
    "f33-build-side-23853",
    "f33-build-side-23863",
    "f33-build-side-23863",
    "f33-build-side-23863",
    "f33-build-side-23865",
    "f33-build-side-23865",
    "f33-build-side-23865",
    "f33-build-side-23869",
    "f33-build-side-23869",
    "f33-build-side-23869",
    "f33-build-side-23871",
    "f33-build-side-23871",
    "f33-build-side-23871",
    "f33-candidate",
    "f33-build",
    "f33-updates-candidate",
    "f33-container-candidate",
    "f33-container-build",
    "f33-container-updates-candidate",
    "f33-coreos-continuous",
    "f33-build",
    "f33-coreos-continuous",
    "f33-infra",
    "f33-infra-build",
    "f33-infra-candidate",
    "f33-nodejs14",
    "f33-nodejs14",
    "f33-nodejs14",
    "f33-python",
    "f33-python",
    "f33-python",
    "module-3a383ba0732c1055",
    "module-3a383ba0732c1055-build",
    "module-3a383ba0732c1055",
    "module-4e782003431f6e88",
    "module-4e782003431f6e88-build",
    "module-4e782003431f6e88",
    "module-512311f662441d1a",
    "module-512311f662441d1a-build",
    "module-512311f662441d1a",
    "module-5be2d05f123faa41",
    "module-5be2d05f123faa41-build",
    "module-5be2d05f123faa41",
    "module-5cd8370d3c6532d6",
    "module-5cd8370d3c6532d6-build",
    "module-5cd8370d3c6532d6",
    "module-8b08096c2be105f5",
    "module-8b08096c2be105f5-build",
    "module-8b08096c2be105f5",
    "module-8ca335b34e88ba66",
    "module-8ca335b34e88ba66-build",
    "module-8ca335b34e88ba66",
    "module-9721006f9645a474",
    "module-9721006f9645a474-build",
    "module-9721006f9645a474",
    "module-9cc85b1dc751823c",
    "module-9cc85b1dc751823c-build",
    "module-9cc85b1dc751823c",
    "module-b787c9c6bbefc539",
    "module-b787c9c6bbefc539-build",
    "module-b787c9c6bbefc539",
    "module-d11cd1edd3bcbf27",
    "module-d11cd1edd3bcbf27-build",
    "module-d11cd1edd3bcbf27",
    "module-d734ed3acfa7f713",
    "module-d734ed3acfa7f713-build",
    "module-d734ed3acfa7f713",
    "module-eclipse-latest-3020200402152434-d2c1e272",
    "module-eclipse-latest-3020200402152434-d2c1e272-build",
    "module-eclipse-latest-3020200402152434-d2c1e272",
    "module-nodejs-10-20180816111713-a5b0195c",
    "module-nodejs-10-20180816111713-a5b0195c-build",
    "module-nodejs-10-20180816111713-a5b0195c",
    "module-nodejs-8-20180816123422-a5b0195c",
    "module-nodejs-8-20180816123422-a5b0195c-build",
    "module-nodejs-8-20180816123422-a5b0195c",
    "module-postgresql-12-3120191125133933-f636be4b",
    "module-postgresql-12-3120191125133933-f636be4b-build",
    "module-postgresql-12-3120191125133933-f636be4b",
    "rawhide",
    "f33-build",
    "f33-updates-candidate",
    "rawhide-container-candidate",
    "f33-container-build",
    "f33-container-updates-candidate",
]
