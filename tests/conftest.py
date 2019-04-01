import datetime
import shutil
import subprocess
import sys
from os import chdir
from pathlib import Path

import pytest
from flexmock import flexmock
from ogr.abstract import PullRequest, PRStatus
from ogr.services.github import GithubService
from ogr.services.pagure import PagureProject, PagureService
from rebasehelper.specfile import SpecFile

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.distgit import DistGit
from packit.upstream import Upstream
from packit.fedpkg import FedPKG
from tests.spellbook import prepare_dist_git_repo, get_test_config
from .spellbook import TARBALL_NAME, UPSTREAM, git_add_n_commit, DISTGIT


@pytest.fixture()
def mock_downstream_remote_functionality(downstream_n_distgit):
    u, d = downstream_n_distgit

    flexmock(DistGit, update_branch=lambda *args, **kwargs: "0.0.0")

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = d / TARBALL_NAME
        hops_filename = "hops"
        hops_path = d / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(["tar", "-cf", str(tarball_path), hops_filename], cwd=d)

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)

    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    # https://stackoverflow.com/questions/45580215/using-flexmock-on-python-modules
    flexmock(sys.modules["packit.bot_api"]).should_receive(
        "get_packit_config_from_repo"
    ).and_return(pc)
    return u, d


@pytest.fixture()
def mock_upstream_remote_functionality(upstream_n_distgit):
    u, d = upstream_n_distgit

    def mocked_pr_create(*args, **kwargs):
        return PullRequest(
            title="",
            id=42,
            status=PRStatus.open,
            url="",
            description="",
            author="",
            source_branch="",
            target_branch="",
            created=datetime.datetime(1969, 11, 11, 11, 11, 11, 11),
        )

    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": str(d)},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject("", "", PagureService()),
        pr_create=mocked_pr_create,
    )

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = d / TARBALL_NAME
        hops_filename = "hops"
        hops_path = d / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(["tar", "-cf", str(tarball_path), hops_filename], cwd=d)

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)

    flexmock(GithubService, get_project=lambda repo, namespace: flexmock())

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        # let's not hammer the production lookaside cache webserver
        is_archive_in_lookaside_cache=lambda archive_path: False,
        build=lambda scratch: None,
    )

    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")

    flexmock(FedPKG, init_ticket=lambda x=None: None, new_sources=mocked_new_sources)

    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    # https://stackoverflow.com/questions/45580215/using-flexmock-on-python-modules
    flexmock(sys.modules["packit.bot_api"]).should_receive(
        "get_packit_config_from_repo"
    ).and_return(pc)
    return u, d


@pytest.fixture()
def upstream_n_distgit(tmpdir):
    t = Path(str(tmpdir))

    u_remote = t / "upstream_remote"
    u_remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=u_remote)

    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    git_add_n_commit(u, tag="0.1.0")

    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    git_add_n_commit(d, push=True, upstream_remote=str(u_remote))
    prepare_dist_git_repo(d)

    return u, d


@pytest.fixture()
def downstream_n_distgit(tmpdir):
    t = Path(str(tmpdir))

    d_remote = t / "downstream_remote"
    d_remote.mkdir()
    subprocess.check_call(["git", "init", "--bare", "."], cwd=d_remote)

    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    git_add_n_commit(d, tag="0.0.0")

    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    git_add_n_commit(u, push=False, upstream_remote=str(d_remote))

    return u, d


@pytest.fixture()
def upstream_instance(upstream_n_distgit):
    u, d = upstream_n_distgit

    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    pc.downstream_project_url = str(d)

    ups = Upstream(c, pc)
    return u, ups


@pytest.fixture()
def distgit_instance(upstream_n_distgit, mock_upstream_remote_functionality):
    u, d = upstream_n_distgit
    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc)
    return d, dg


@pytest.fixture()
def api_instance(upstream_n_distgit):
    u, d = upstream_n_distgit

    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)

    api = PackitAPI(c, pc)
    return u, d, api
