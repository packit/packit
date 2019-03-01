import datetime
import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock
from rebasehelper.specfile import SpecFile

from ogr.abstract import PullRequest, PRStatus
from ogr.services.pagure import PagureProject, PagureService
from packit.distgit import DistGit
from packit.utils import FedPKG

THIS_DIR = Path(__file__).parent
DATA_DIR = THIS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
DISTGIT = DATA_DIR / "dist_git"
TARBALL_NAME = "beerware-0.1.0.tar.gz"


@pytest.fixture()
def beer(tmpdir):
    t = Path(str(tmpdir))
    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    subprocess.check_call(["git", "init", "."], cwd=u)
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=u)
    subprocess.check_call(["git", "remote", "add", "origin", "https://lol.wat"], cwd=u)

    subprocess.check_call(["git", "init", "."], cwd=d)
    subprocess.check_call(["git", "add", "."], cwd=d)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=d)
    subprocess.check_call(["git", "remote", "add", "origin", "https://lol.wat"], cwd=d)
    return u, d


@pytest.fixture()
def mock_update_workflow(beer):
    u, d = beer

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
            created=datetime.datetime(1969, 11, 11, 11, 11, 11, 11)
        )
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": "https://ehm.nope/"},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject(
            "", "", PagureService()
        ),
        pr_create=mocked_pr_create
    )

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = d / TARBALL_NAME
        hops_filename = "hops"
        hops_path = d / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(["tar", "-cf", str(tarball_path), hops_filename], cwd=d)

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)

    flexmock(DistGit, push_to_fork=lambda branch_name: None)

    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")
    flexmock(FedPKG, init_ticket=lambda x=None: None, new_sources=mocked_new_sources)
