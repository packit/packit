# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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

"""
Tests for Upstream class
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from flexmock import flexmock
from ogr import GithubService
from packit.config import Config, get_local_package_config
from packit.exceptions import PackitException, PackitSRPMException
from packit.local_project import LocalProject
from packit.specfile import Specfile
from packit.upstream import Upstream
from packit.utils import cwd
from tests.spellbook import (
    EMPTY_CHANGELOG,
    initiate_git_repo,
    get_test_config,
    build_srpm,
)


def test_get_spec_version(upstream_instance):
    u, ups = upstream_instance
    assert ups.get_specfile_version() == "0.1.0"


def test_get_current_version(upstream_instance):
    u, ups = upstream_instance

    assert ups.get_current_version() == "0.1.0"


@pytest.mark.parametrize(
    "m_v,exp",
    (
        ("1.1000.1000000", "1.1000.1000000"),
        (None, "0.1.0"),
        ("0.0.3", "0.1.0"),
        ("176", "176"),
    ),
)
def test_get_version(upstream_instance, m_v, exp):
    u, ups = upstream_instance
    flexmock(Specfile, get_upstream_version=lambda **kw: m_v)

    assert ups.get_version() == exp

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    assert ups.get_current_version() == "0.1.0"


def test_get_version_macro(upstream_instance):
    u, ups = upstream_instance

    data = "import setuptools \nsetuptools.setup(version='1')"
    setup_path = u.joinpath("setup.py")
    with open(u.joinpath("setup.py"), "w+") as setup:
        setup.write(data)

    data = u.joinpath("beer.spec").read_text()
    data = data.replace("0.1.0", "%(python3 %{S:" + str(setup_path) + "} --version)")
    with open(u.joinpath("beer.spec"), "w") as f:
        f.write(data)

    assert ups.get_specfile_version() == "1"


def test_set_spec_ver(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.specfile.set_spec_version(version=new_ver, changelog_entry="- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "- asdqwe" in u.joinpath("beer.spec").read_text()


def test_set_spec_ver_empty_changelog(tmpdir):
    t = Path(str(tmpdir))

    u_remote_path = t / "upstream_remote"
    u_remote_path.mkdir(parents=True, exist_ok=True)

    subprocess.check_call(["git", "init", "--bare", "."], cwd=u_remote_path)

    u = t / "upstream_git"
    shutil.copytree(EMPTY_CHANGELOG, u)
    initiate_git_repo(u, tag="0.1.0")

    with cwd(tmpdir):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        lp = LocalProject(working_dir=str(u))

        ups = Upstream(c, pc, lp)

    new_ver = "1.2.3"
    ups.specfile.set_spec_version(version=new_ver, changelog_entry="- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "%changelog" not in u.joinpath("beer.spec").read_text()


def change_source_ext(upstream, extension):
    preamble = upstream.specfile.spec_content.section("%package")
    for i, line in enumerate(preamble):
        if line.startswith("Source"):
            source = line.split()[1]
            start = line.index(source)
            source = source.rstrip("".join(Path(source).suffixes)) + extension
            preamble[i] = line[:start] + source
    upstream.specfile.save()


@pytest.mark.parametrize(
    "extension", [".tar.gz", ".tar.bz2"], ids=[".tar.gz", ".tar.bz2"]
)
def test_create_archive(upstream_instance, extension):
    u, ups = upstream_instance
    change_source_ext(ups, extension)

    ups.create_archive()

    assert u.glob(f"*{extension}")

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()

    # we enforce .tar.gz now
    assert len(list(u.glob("*.tar.gz"))) == 1


def test_create_uncommon_archive(upstream_instance):
    u, ups = upstream_instance
    change_source_ext(ups, ".cpio")
    ups.create_archive()
    # we enforce .tar.gz now
    assert len(list(u.glob("*.tar.gz"))) == 1


def test_fix_spec(upstream_instance):
    u, ups = upstream_instance

    ups.package_config.upstream_package_name = None
    with pytest.raises(PackitException) as ex:
        ups.fix_spec("asd.tar.gz", "1.2.3", "abcdef123")

    assert '"upstream_package_name" is not set' in str(ex.value)


def test_create_srpm(upstream_instance, tmpdir):
    u, ups = upstream_instance

    with pytest.raises(PackitSRPMException) as exc:
        ups.create_srpm()
    assert "Bad source" in str(exc.value)

    ups.create_archive()
    srpm = ups.create_srpm()

    assert srpm.exists()

    srpm_path = Path(tmpdir).joinpath("custom.src.rpm")

    ups.prepare_upstream_for_srpm_creation()
    srpm = ups.create_srpm(srpm_path=srpm_path)
    r = re.compile(r"^- Development snapshot \(\w{8}\)$")
    for l in ups.specfile.spec_content.section("%changelog"):
        if r.match(l):
            break
    else:
        assert False, "Didn't find the correct line in the spec file."
    assert srpm.exists()
    build_srpm(srpm)


def test_create_srpm_git_desc_release(upstream_instance, tmpdir):
    u, ups = upstream_instance
    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()
    ups.prepare_upstream_for_srpm_creation()
    srpm = ups.create_srpm()
    assert srpm.exists()
    build_srpm(srpm)
    assert re.match(r".+beer-0.1.0-1.\d+.fc\d{2}.src.rpm$", str(srpm))


def test_github_app(upstream_instance, tmpdir):
    u, ups = upstream_instance
    t = Path(tmpdir)

    fake_cert_path = t / "fake-cert.pem"
    fake_cert_path.write_text("hello!")

    user_config_file_path = t / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        f"authentication:\n"
        f"    github.com:\n"
        f"        github_app_private_key_path: {fake_cert_path}\n"
        f"        github_app_id: qwe\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmpdir)
    )
    ups.config = Config.get_user_config()
    assert (
        GithubService(
            github_app_private_key_path=str(fake_cert_path), github_app_id="qwe"
        )
        in ups.config.services
    )
