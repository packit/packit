import os

from rebasehelper.specfile import SpecFile

from packit.api import PackitAPI
from packit.config import Config
from tests.conftest import TARBALL_NAME


def test_basic_local_update(beer, mock_update_workflow):
    """ basic propose-update test: mock remote API, use local upstream and dist-git """
    u, d = beer

    os.chdir(u)
    c = Config()
    c.dist_git_path = d
    p = PackitAPI(c)
    p.update("master")

    assert os.path.exists(os.path.join(d, TARBALL_NAME))
    spec = SpecFile(os.path.join(d, "beer.spec"), None)
    assert spec.get_full_version() == "0.1.0"
