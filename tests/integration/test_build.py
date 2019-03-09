from os import chdir

from packit.api import PackitAPI
from packit.config import get_local_package_config
from tests.spellbook import get_test_config


def test_basic_build(upstream_n_distgit, mock_remote_functionality):
    u, d = upstream_n_distgit
    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    pc.downstream_project_url = str(d)

    api = PackitAPI(c, pc)
    api.build("master")
