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

import shutil
import subprocess
from pathlib import Path
from typing import Tuple

import pytest

from packit.utils import cwd
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


def get_git_repo_and_remote(
    target_dir: Path, repo_template_path: Path
) -> Tuple[Path, Path]:
    """
    :param target_dir: tmpdir from pytest - we'll work here
    :param repo_template_path: git repo template from tests/data/
    """
    u_remote_path = target_dir / f"upstream_remote-{repo_template_path.name}"
    u_remote_path.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "init", "--bare", "."], cwd=u_remote_path)

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
    subprocess.check_call(["git", "init", "--bare", "."], cwd=d_remote_path)

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
    subprocess.check_call(["git", "init", "--bare", "."], cwd=d_remote_path)

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
