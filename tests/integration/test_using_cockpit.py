"""
E2E tests which utilize cockpit projects
"""
import shutil
from pathlib import Path

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.distgit import DistGit
from packit.fedpkg import FedPKG
from packit.local_project import LocalProject
from packit.utils import cwd
from tests.spellbook import UP_COCKPIT_OSTREE, initiate_git_repo, get_test_config


@pytest.fixture()
def cockpit_ostree(tmpdir):
    t = Path(str(tmpdir))

    u = t / "up"
    shutil.copytree(UP_COCKPIT_OSTREE, u)
    initiate_git_repo(u, tag="179")

    return u


def test_update_on_cockpit_ostree(cockpit_ostree):
    def mocked_new_sources(sources=None):
        if not Path(sources).is_file():
            raise RuntimeError("archive does not exist")

    flexmock(FedPKG, init_ticket=lambda x=None: None, new_sources=mocked_new_sources)

    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        is_archive_in_lookaside_cache=lambda archive_path: False,
    )
    flexmock(
        PackitAPI,
        push_and_create_pr=lambda pr_title, pr_description, dist_git_branch: None,
    )

    pc = get_local_package_config(str(cockpit_ostree))
    up_lp = LocalProject(working_dir=str(cockpit_ostree))
    c = get_test_config()

    api = PackitAPI(c, pc, up_lp)
    with cwd(cockpit_ostree):
        api.sync_release(
            "master",
            use_local_content=False,
            version="179",
            force_new_sources=False,
            create_pr=True,
        )

    assert api.dg.download_upstream_archive().is_file()
