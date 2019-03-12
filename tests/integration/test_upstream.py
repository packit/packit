"""
Tests for Upstream class
"""
from os import chdir

from packit.config import get_local_package_config
from packit.upstream import Upstream
from tests.spellbook import get_test_config


def test_basic_local_update(upstream_n_distgit):
    """ basic propose-update test: mock remote API, use local upstream and dist-git """
    u, d = upstream_n_distgit

    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)

    ups = Upstream(c, pc)

    assert ups.get_specfile_version() == "0.1.0"
