"""
Tests for Upstream class
"""
import re
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock
from rebasehelper.versioneer import versioneers_runner

from packit.exceptions import PackitException
from tests.spellbook import does_bumpspec_know_new


def test_get_spec_version(upstream_instance):
    u, ups = upstream_instance
    assert ups.get_specfile_version() == "0.1.0"


def test_get_current_version(upstream_instance):
    u, ups = upstream_instance

    assert ups.get_current_version() == "0.1.0"


@pytest.mark.parametrize(
    "m_v,exp", (("1.1000.1000000", "1.1000.1000000"), (None, "0.1.0"))
)
def test_get_version(upstream_instance, m_v, exp):
    u, ups = upstream_instance
    flexmock(versioneers_runner, run=lambda **kw: m_v)

    assert ups.get_version() == exp

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    # 0.1.0.1.ge98cee1
    assert re.match(r"0\.1\.0\.1\.\w{8}", ups.get_current_version())


@pytest.mark.skipif(
    not does_bumpspec_know_new(),
    reason="Current version of rpmdev-bumpspec doesn't understand --new option.",
)
def test_bumpspec(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.bump_spec(version=new_ver, changelog_entry="asdqwe")

    assert ups.get_specfile_version() == new_ver


def test_set_spec_ver(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.set_spec_version(version=new_ver, changelog_entry="- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "- asdqwe" in u.joinpath("beer.spec").read_text()


def test_create_archive(upstream_instance):
    u, ups = upstream_instance

    ups.create_archive()

    assert u.glob("*.tar.gz")

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()

    assert len(list(u.glob("*.tar.gz"))) == 2


def test_create_srpm(upstream_instance, tmpdir):
    u, ups = upstream_instance

    with pytest.raises(PackitException) as exc:
        ups.create_srpm()
    assert "SRPM could not be created. Is the archive present?" in str(exc.value)

    ups.create_archive()
    srpm = ups.create_srpm()

    assert srpm.exists()

    srpm_path = Path(tmpdir).joinpath("custom.src.rpm")
    srpm = ups.create_srpm(srpm_path=srpm_path)
    assert srpm.exists()
