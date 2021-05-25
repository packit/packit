# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil
from pathlib import Path
from typing import Tuple
import subprocess
import tempfile

import pytest
from flexmock import flexmock

from packit.utils.commands import cwd
from packit.utils.repo import create_new_repo
from tests.spellbook import (
    initiate_git_repo,
    UPSTREAM,
    prepare_dist_git_repo,
    DISTGIT,
    DG_OGR,
    UPSTREAM_SPEC_NOT_IN_ROOT,
    UPSTREAM_WITH_MUTLIPLE_SOURCES,
    UPSTREAM_WEIRD_SOURCES,
)


# define own tmp_path fixture for older version of pytest (Centos)
try:
    from _pytest import tmpdir

    _ = tmpdir.tmp_path
except (ImportError, AttributeError, KeyError):

    @pytest.fixture()
    def tmp_path():
        TMP_DIR = "/tmp/pytest_tmp_path/"
        Path(TMP_DIR).mkdir(exist_ok=True, parents=True)
        return Path(tempfile.mkdtemp(prefix=TMP_DIR))


def get_git_repo_and_remote(
    target_dir: Path, repo_template_path: Path
) -> Tuple[Path, Path]:
    """
    :param target_dir: tmpdir from pytest - we'll work here
    :param repo_template_path: git repo template from tests/data/
    """
    u_remote_path = target_dir / f"upstream_remote-{repo_template_path.name}"
    u_remote_path.mkdir(parents=True, exist_ok=True)
    create_new_repo(u_remote_path, ["--bare"])

    u = target_dir / f"local_clone-{repo_template_path.name}"
    shutil.copytree(repo_template_path, u)
    initiate_git_repo(u, tag="0.1.0", push=True, upstream_remote=str(u_remote_path))

    return u, u_remote_path


@pytest.fixture()
def upstream_and_remote(tmp_path) -> Tuple[Path, Path]:
    return get_git_repo_and_remote(tmp_path, UPSTREAM)


@pytest.fixture()
def upstream_and_remote_with_multiple_sources(tmp_path) -> Tuple[Path, Path]:
    return get_git_repo_and_remote(tmp_path, UPSTREAM_WITH_MUTLIPLE_SOURCES)


@pytest.fixture()
def upstream_and_remote_weird_sources(tmp_path) -> Tuple[Path, Path]:
    return get_git_repo_and_remote(tmp_path, UPSTREAM_WEIRD_SOURCES)


@pytest.fixture()
def upstream_spec_not_in_root(tmp_path) -> Tuple[Path, Path]:
    return get_git_repo_and_remote(tmp_path, UPSTREAM_SPEC_NOT_IN_ROOT)


@pytest.fixture()
def distgit_and_remote(tmp_path) -> Tuple[Path, Path]:
    d_remote_path = tmp_path / "dist_git_remote"
    d_remote_path.mkdir(parents=True, exist_ok=True)
    create_new_repo(d_remote_path, ["--bare"])

    d = tmp_path / "dist_git"
    shutil.copytree(DISTGIT, d)
    initiate_git_repo(
        d,
        push=True,
        remotes=[
            ("origin", str(d_remote_path)),
            ("i_am_distgit", "https://src.fedoraproject.org/rpms/python-ogr"),
        ],
    )
    prepare_dist_git_repo(d)

    return d, d_remote_path


@pytest.fixture()
def ogr_distgit_and_remote(tmp_path) -> Tuple[Path, Path]:
    d_remote_path = tmp_path / "ogr_dist_git_remote"
    d_remote_path.mkdir(parents=True, exist_ok=True)
    create_new_repo(d_remote_path, ["--bare"])

    d = tmp_path / "ogr_dist_git"
    shutil.copytree(DG_OGR, d)
    initiate_git_repo(
        d,
        push=True,
        remotes=[
            ("origin", str(d_remote_path)),
            ("i_am_distgit", "https://src.fedoraproject.org/rpms/python-ogr"),
        ],
    )
    prepare_dist_git_repo(d)
    return d, d_remote_path


@pytest.fixture(params=["upstream", "ogr-distgit"])
def upstream_or_distgit_path(
    request, upstream_and_remote, distgit_and_remote, ogr_distgit_and_remote
):
    """
    Parametrize the test to upstream, downstream [currently skipped] and ogr distgit
    """
    cwd_path = {
        "upstream": upstream_and_remote[0],
        "distgit": distgit_and_remote[0],
        "ogr-distgit": ogr_distgit_and_remote[0],
    }[request.param]

    return cwd_path


@pytest.fixture(
    params=["upstream", "distgit", "ogr-distgit", "upstream-with-multiple-sources"]
)
def cwd_upstream_or_distgit(
    request,
    upstream_and_remote,
    distgit_and_remote,
    ogr_distgit_and_remote,
    upstream_and_remote_with_multiple_sources,
):
    """
    Run the code from upstream, downstream and ogr-distgit.

    When using be careful to
        - specify this fixture in the right place
        (the order of the parameters means order of the execution)
        - to not overwrite the cwd in the other fixture or in the test itself
    """
    cwd_path = {
        "upstream": upstream_and_remote[0],
        "distgit": distgit_and_remote[0],
        "ogr-distgit": ogr_distgit_and_remote[0],
        "upstream-with-multiple-sources": upstream_and_remote_with_multiple_sources[0],
    }[request.param]

    with cwd(cwd_path):
        yield cwd_path


@pytest.fixture
def copr_client_mock(get_list_return=None):
    get_list_return = {
        "centos-stream-aarch64": "",
        "custom-1-x86_64": "",
        "epel-6-x86_64": "",
        "epel-8-x86_64": "",
        "fedora-31-aarch64": "",
        "fedora-31-armhfp": "This is emulated on x86_64",
        "fedora-31-x86_64": "",
        "fedora-32-armhfp": "This is emulated on x86_64",
        "fedora-32-i386": "Not-released Koji packages",
        "fedora-32-s390x": "This is emulated on x86_64",
        "fedora-32-x86_64": "",
        "fedora-33-x86_64": "",
        "fedora-eln-x86_64": "",
        "fedora-rawhide-aarch64": "",
        "fedora-rawhide-x86_64": "",
    }

    copr_mock = flexmock(mock_chroot_proxy=flexmock(get_list=lambda: get_list_return))
    return copr_mock


@pytest.fixture(autouse=True, scope="function")
def configure_git():
    CMDS = [
        ["git", "config", "--global", "user.email", "packit@redhat.com"],
        ["git", "config", "--global", "user.name", "Packit Test"],
    ]
    # verify that git is already configured
    try:
        output = subprocess.check_output(["git", "config", "-l", "--global"])
    except subprocess.CalledProcessError:
        output = ""
    if "user.name" in output if isinstance(output, str) else output.decode():
        return
    for item in CMDS:
        subprocess.call(item)
