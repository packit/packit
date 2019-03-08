import copy
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
from packit.bot_api import PackitBotAPI
from packit.config import Config, get_local_package_config
from packit.distgit import DistGit
from packit.fed_mes_consume import Consumerino
from packit.utils import FedPKG
from tests.spellbook import git_set_user_email

THIS_DIR = Path(__file__).parent
TESTS_DIR = THIS_DIR.parent
DATA_DIR = TESTS_DIR / "data"
UPSTREAM = DATA_DIR / "upstream_git"
DISTGIT = DATA_DIR / "dist_git"
TARBALL_NAME = "beerware-0.1.0.tar.gz"


def get_test_config():
    conf = Config()
    conf._pagure_user_token = "test"
    conf._pagure_fork_token = "test"
    conf._github_token = "test"
    return conf


def git_add_n_commit(directory, tag=None):
    subprocess.check_call(["git", "init", "."], cwd=directory)
    git_set_user_email(directory)
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=directory)
    if tag:
        subprocess.check_call(["git", "tag", tag], cwd=directory)
    subprocess.check_call(["git", "remote", "add", "origin", "https://lol.wat"], cwd=directory)


@pytest.fixture()
def github_release_fedmsg():
    return {
        "msg_id": "2019-a5034b55-339d-4fa5-a72b-db74579aeb5a",
        "topic": "org.fedoraproject.prod.github.release",
        "msg": {
            "repository": {
                "full_name": "brewery/beer",
                "owner": {
                    "login": "brewery",
                },
                "name": "beer",
                "html_url": "https://github.com/brewery/beer",
            },
            "release": {
                "body": "Changelog content will be here",
                "tag_name": "0.1.0",
                "created_at": "2019-02-28T18:48:27Z",
                "published_at": "2019-02-28T18:51:10Z",
                "draft": False,
                "prerelease": False,
                "name": "Beer 0.1.0 is gooooood"
            },
            "action": "published",
        }
    }


@pytest.fixture()
def upstream_n_distgit(tmpdir):
    t = Path(str(tmpdir))

    u = t / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    git_add_n_commit(u, tag="0.1.0")

    d = t / "dist_git"
    shutil.copytree(DISTGIT, d)
    git_add_n_commit(d)

    return u, d


@pytest.fixture()
def mock_update_workflow(upstream_n_distgit):
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
            created=datetime.datetime(1969, 11, 11, 11, 11, 11, 11)
        )
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": str(d)},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject(
            "", "", PagureService()
        ),
        pr_create=mocked_pr_create
    )
    flexmock(
        GithubService,
        get_project=None
    )

    def mock_download_remote_sources():
        """ mock download of the remote archive and place it into dist-git repo """
        tarball_path = d / TARBALL_NAME
        hops_filename = "hops"
        hops_path = d / hops_filename
        hops_path.write_text("Cascade\n")
        subprocess.check_call(["tar", "-cf", str(tarball_path), hops_filename], cwd=d)

    flexmock(SpecFile, download_remote_sources=mock_download_remote_sources)

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        # let's not hammer the production lookaside cache webserver
        is_archive_on_lookaside_cache=lambda archive_path: False,
    )

    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")
    flexmock(FedPKG, init_ticket=lambda x=None: None, new_sources=mocked_new_sources)

    pc = get_local_package_config(str(u))
    pc.downstream_project_url = str(d)
    pc.upstream_project_url = str(u)
    # https://stackoverflow.com/questions/45580215/using-flexmock-on-python-modules
    flexmock(sys.modules["packit.bot_api"]).should_receive("get_packit_config_from_repo").and_return(pc)
    return u, d


def test_basic_local_update(upstream_n_distgit, mock_update_workflow):
    """ basic propose-update test: mock remote API, use local upstream and dist-git """
    u, d = upstream_n_distgit

    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    pc.downstream_project_url = str(d)
    api = PackitAPI(c, pc)
    api.sync_release("master", "0.1.0")

    assert (d / TARBALL_NAME).is_file()
    spec = SpecFile(str(d / "beer.spec"), None)
    assert spec.get_full_version() == "0.1.0"


def test_single_message(github_release_fedmsg, mock_update_workflow):
    u, d = mock_update_workflow

    conf = get_test_config()
    api = PackitBotAPI(conf)
    api.sync_upstream_release_with_fedmsg(github_release_fedmsg)
    assert (d / TARBALL_NAME).is_file()
    spec = SpecFile(str(d / "beer.spec"), None)
    assert spec.get_full_version() == "0.1.0"


def test_loop(mock_update_workflow, github_release_fedmsg):
    def mocked_iter_releases():
        msg = copy.deepcopy(github_release_fedmsg)
        yield msg["topic"], msg
    flexmock(Consumerino, iterate_releases=mocked_iter_releases)
    conf = get_test_config()
    api = PackitBotAPI(conf)
    api.watch_upstream_release()
